"""Tests for POST /api/v1/contact (D-04)."""
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app


class FakeAcquireCtx:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        conn = MagicMock()

        async def fetch(*a, **kw):
            return self._rows

        conn.fetch = fetch
        return conn

    async def __aexit__(self, *a):
        return False


class FakePool:
    def __init__(self, rows):
        self._rows = rows

    def acquire(self):
        return FakeAcquireCtx(self._rows)


def _install(rows):
    app.state.db_pool = FakePool(rows)


@pytest.mark.asyncio
async def test_missing_subject_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/contact", data={"message": "hello"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_message_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/contact", data={"subject": "hi"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_no_admins_returns_500(monkeypatch):
    _install([])
    monkeypatch.setenv("SMTP_USER", "x@y.z")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/contact", data={"subject": "s", "message": "m"})
    assert resp.status_code == 500
    assert "No admin recipients" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_post_sends_to_all_admins(monkeypatch):
    _install([{"email": "a@x.com"}, {"email": "b@x.com"}])
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-pw")
    with patch("app.modules.contact.router.smtplib.SMTP") as mock_smtp:
        smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = smtp_instance
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/contact",
                data={
                    "subject": "s",
                    "message": "m",
                    "sender_name": "Alice",
                    "sender_email": "alice@x.com",
                    "sender_institution": "U",
                },
            )
        assert resp.status_code == 200
        assert resp.json() == {"status": "sent"}
        sendmail_call = smtp_instance.sendmail.call_args
        assert sendmail_call[0][1] == ["a@x.com", "b@x.com"]


@pytest.mark.asyncio
async def test_pdf_attachment_included(monkeypatch):
    _install([{"email": "a@x.com"}])
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    with patch("app.modules.contact.router.smtplib.SMTP") as mock_smtp:
        smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = smtp_instance
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"pdf_attachment": ("r.pdf", b"%PDF-1.4 fake", "application/pdf")}
            resp = await client.post(
                "/api/v1/contact",
                data={"subject": "s", "message": "m"},
                files=files,
            )
        assert resp.status_code == 200
        message_str = smtp_instance.sendmail.call_args[0][2]
        assert "analysis_report.pdf" in message_str


@pytest.mark.asyncio
async def test_oversized_pdf_rejected(monkeypatch):
    _install([{"email": "a@x.com"}])
    monkeypatch.setenv("SMTP_USER", "s@g.c")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    big = b"X" * (5 * 1024 * 1024 + 10)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"pdf_attachment": ("big.pdf", big, "application/pdf")}
        resp = await client.post(
            "/api/v1/contact",
            data={"subject": "s", "message": "m"},
            files=files,
        )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_recipients_from_db_not_user_input(monkeypatch):
    _install([{"email": "legit-admin@x.com"}])
    monkeypatch.setenv("SMTP_USER", "s@g.c")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    with patch("app.modules.contact.router.smtplib.SMTP") as mock_smtp:
        smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = smtp_instance
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/contact",
                data={
                    "subject": "s",
                    "message": "m",
                    "sender_email": "attacker@evil.com",
                },
            )
        assert resp.status_code == 200
        recipients = smtp_instance.sendmail.call_args[0][1]
        assert recipients == ["legit-admin@x.com"]
        assert "attacker@evil.com" not in recipients
