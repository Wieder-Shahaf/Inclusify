"""Tests for POST /api/v1/contact (D-04)."""
import base64

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.users import current_active_user


class FakeUser:
    id = "11111111-1111-1111-1111-111111111111"
    email = "signed-in@x.com"
    full_name = "Signed In"
    institution = "Test U"


@pytest.fixture(autouse=True)
def _clean_contact_env(monkeypatch):
    # Reset per-process rate-limit state and drop any CONTACT_RECIPIENTS
    # leaking from a loaded .env so tests exercise the DB fallback by default.
    from app.modules.contact import router as contact_router
    contact_router._rate_store.clear()
    monkeypatch.delenv("CONTACT_RECIPIENTS", raising=False)
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    # Default: requests are authenticated. Guest test removes this override.
    app.dependency_overrides[current_active_user] = lambda: FakeUser()
    yield
    app.dependency_overrides.pop(current_active_user, None)


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


def _mock_resend():
    """Patch httpx.AsyncClient so no real HTTP fires. Returns (patcher, post_mock);
    the post mock captures the JSON payload sent to Resend."""
    post_mock = AsyncMock(return_value=MagicMock())  # resp.raise_for_status() is a no-op
    client = MagicMock()
    client.post = post_mock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    patcher = patch("app.modules.contact.router.httpx.AsyncClient", return_value=cm)
    return patcher, post_mock


@pytest.mark.asyncio
async def test_guest_rejected_401():
    # Remove the auth override so the real dependency runs and rejects the guest.
    app.dependency_overrides.pop(current_active_user, None)
    _install([{"email": "a@x.com"}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/contact", data={"subject": "s", "message": "m"})
    assert resp.status_code == 401


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
async def test_no_admins_returns_500():
    _install([])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/contact", data={"subject": "s", "message": "m"})
    assert resp.status_code == 500
    assert "No admin recipients" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_missing_api_key_returns_500(monkeypatch):
    _install([{"email": "a@x.com"}])
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/contact", data={"subject": "s", "message": "m"})
    assert resp.status_code == 500
    assert "API key" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_valid_post_sends_to_all_admins():
    _install([{"email": "a@x.com"}, {"email": "b@x.com"}])
    patcher, post_mock = _mock_resend()
    with patcher:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/contact",
                data={"subject": "s", "message": "m"},
            )
    assert resp.status_code == 200
    assert resp.json() == {"status": "sent"}
    payload = post_mock.call_args.kwargs["json"]
    assert payload["to"] == ["a@x.com", "b@x.com"]
    # reply_to and the body sender come from the authenticated user.
    assert payload["reply_to"] == "signed-in@x.com"
    assert "signed-in@x.com" in payload["text"]


@pytest.mark.asyncio
async def test_sender_identity_from_auth_not_client():
    # Even if a client smuggles sender_email in the form, it is ignored:
    # the authenticated user's email is what's used.
    _install([{"email": "legit-admin@x.com"}])
    patcher, post_mock = _mock_resend()
    with patcher:
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
    payload = post_mock.call_args.kwargs["json"]
    assert payload["to"] == ["legit-admin@x.com"]
    assert payload["reply_to"] == "signed-in@x.com"
    assert "attacker@evil.com" not in payload["text"]


@pytest.mark.asyncio
async def test_pdf_attachment_included():
    _install([{"email": "a@x.com"}])
    patcher, post_mock = _mock_resend()
    with patcher:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"pdf_attachment": ("r.pdf", b"%PDF-1.4 fake", "application/pdf")}
            resp = await client.post(
                "/api/v1/contact",
                data={"subject": "s", "message": "m"},
                files=files,
            )
    assert resp.status_code == 200
    attachments = post_mock.call_args.kwargs["json"]["attachments"]
    assert attachments[0]["filename"] == "analysis_report.pdf"
    assert base64.b64decode(attachments[0]["content"]) == b"%PDF-1.4 fake"


@pytest.mark.asyncio
async def test_oversized_pdf_rejected():
    _install([{"email": "a@x.com"}])
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
async def test_contact_recipients_env_overrides_db(monkeypatch):
    # site_admin in DB should be ignored when CONTACT_RECIPIENTS is set.
    _install([{"email": "admin@x.com"}])
    monkeypatch.setenv("CONTACT_RECIPIENTS", "support@x.com , second@x.com")
    patcher, post_mock = _mock_resend()
    with patcher:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/contact", data={"subject": "s", "message": "m"}
            )
    assert resp.status_code == 200
    assert post_mock.call_args.kwargs["json"]["to"] == ["support@x.com", "second@x.com"]


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_5_per_user():
    _install([{"email": "a@x.com"}])
    patcher, _ = _mock_resend()
    with patcher:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(5):
                ok = await client.post("/api/v1/contact", data={"subject": "s", "message": "m"})
                assert ok.status_code == 200
            blocked = await client.post("/api/v1/contact", data={"subject": "s", "message": "m"})
    assert blocked.status_code == 429
