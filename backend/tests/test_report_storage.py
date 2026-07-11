"""Tests for per-run report storage (PUT/GET /api/v1/users/me/history/{run_id}/report)
and the UTC tagging of history timestamps.
"""
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from jose import jwt

REPORT_PDF = b"%PDF-1.4 fake report bytes"


def auth_headers(user_id=None):
    from app.core.config import settings

    token = jwt.encode(
        {
            "sub": str(user_id or uuid.uuid4()),
            "role": "user",
            "aud": "fastapi-users:auth",
            "exp": int(time.time()) + 3600,
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def report_url(run_id=None):
    return f"/api/v1/users/me/history/{run_id or uuid.uuid4()}/report"


def own_run(monkeypatch, owned=True):
    monkeypatch.setattr("app.db.repository.run_owned_by_user", AsyncMock(return_value=owned))


@pytest.mark.asyncio
async def test_upload_report_requires_auth(test_client):
    resp = await test_client.put(report_url(), content=REPORT_PDF)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_report_unowned_run_404(test_client, monkeypatch):
    own_run(monkeypatch, owned=False)
    resp = await test_client.put(report_url(), content=REPORT_PDF, headers=auth_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_report_success(test_client, monkeypatch):
    own_run(monkeypatch)
    upload = AsyncMock(return_value="blob://texts/reports/x.pdf")
    monkeypatch.setattr("app.core.blob_storage.upload_report", upload)
    run_id = uuid.uuid4()
    resp = await test_client.put(report_url(run_id), content=REPORT_PDF, headers=auth_headers())
    assert resp.status_code == 204
    upload.assert_awaited_once_with(str(run_id), REPORT_PDF)


@pytest.mark.asyncio
async def test_upload_report_rejects_non_pdf(test_client, monkeypatch):
    own_run(monkeypatch)
    resp = await test_client.put(report_url(), content=b"not a pdf", headers=auth_headers())
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_report_size_cap(test_client, monkeypatch):
    own_run(monkeypatch)
    monkeypatch.setattr("app.modules.profile.router._MAX_REPORT_BYTES", 10)
    resp = await test_client.put(report_url(), content=REPORT_PDF, headers=auth_headers())
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_report_storage_unavailable_503(test_client, monkeypatch):
    own_run(monkeypatch)
    monkeypatch.setattr("app.core.blob_storage.upload_report", AsyncMock(return_value=None))
    resp = await test_client.put(report_url(), content=REPORT_PDF, headers=auth_headers())
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_download_report_success(test_client, monkeypatch):
    own_run(monkeypatch)
    monkeypatch.setattr("app.core.blob_storage.download_report", AsyncMock(return_value=REPORT_PDF))
    resp = await test_client.get(report_url(), headers=auth_headers())
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == REPORT_PDF


@pytest.mark.asyncio
async def test_download_report_missing_404(test_client, monkeypatch):
    own_run(monkeypatch)
    monkeypatch.setattr("app.core.blob_storage.download_report", AsyncMock(return_value=None))
    resp = await test_client.get(report_url(), headers=auth_headers())
    assert resp.status_code == 404


def test_history_timestamps_are_utc_tagged():
    from app.modules.profile.router import _utc_iso

    assert _utc_iso(None) is None
    # Naive DB timestamps (TIMESTAMP columns storing UTC) must serialize with
    # an explicit UTC offset so browsers don't parse them as local time.
    assert _utc_iso(datetime(2026, 7, 6, 15, 25, 18)).endswith("+00:00")
