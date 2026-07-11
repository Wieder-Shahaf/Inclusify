"""Tests for the S3-compatible object storage client (Stack A §2.1).

Uses moto's in-process S3 mock, so these run in CI with no MinIO/R2 — they
exercise the real boto3 wiring, the blob://<bucket>/<key> ref contract, the
content-addressed skip, and the disabled (no-credentials) path.
"""
import pytest

pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

from app.core import blob_storage as b  # noqa: E402
from app.core.config import settings  # noqa: E402

SHA = "d" * 64


def _configure(monkeypatch):
    # Empty endpoint => boto3 resolves AWS endpoints, which moto intercepts.
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "testing")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setattr(settings, "S3_BUCKET", "texts")
    # moto needs a real AWS region when no endpoint_url is given ("auto" is R2-only).
    monkeypatch.setattr(settings, "S3_REGION", "us-east-1")


@pytest.mark.asyncio
async def test_disabled_when_no_credentials(monkeypatch):
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "")
    assert b._s3_enabled() is False
    assert await b.upload_text(SHA, "hi") is None
    assert await b.upload_file_bytes(SHA, "f.pdf", b"x") is None


@pytest.mark.asyncio
async def test_upload_text_round_trip_utf8(monkeypatch):
    _configure(monkeypatch)
    with mock_aws():
        await b.ensure_container()
        ref = await b.upload_text(SHA, "שלום hello world")
        assert ref == f"blob://texts/{SHA}.txt"
        client = b._get_client()
        body = client.get_object(Bucket="texts", Key=f"{SHA}.txt")["Body"].read().decode("utf-8")
        assert body == "שלום hello world"


@pytest.mark.asyncio
async def test_upload_file_bytes_key_layout_and_ext_lowercased(monkeypatch):
    _configure(monkeypatch)
    with mock_aws():
        await b.ensure_container()
        ref = await b.upload_file_bytes("c" * 64, "Paper.PDF", b"%PDF-1.4")
        assert ref == f"blob://texts/files/{'c' * 64}.pdf"
        client = b._get_client()
        data = client.get_object(Bucket="texts", Key=f"files/{'c' * 64}.pdf")["Body"].read()
        assert data == b"%PDF-1.4"


@pytest.mark.asyncio
async def test_upload_text_is_idempotent_content_addressed(monkeypatch):
    _configure(monkeypatch)
    with mock_aws():
        await b.ensure_container()
        r1 = await b.upload_text("e" * 64, "v1")
        # Same key (content-addressed) => second upload is skipped, keeps v1.
        r2 = await b.upload_text("e" * 64, "v2-should-be-ignored")
        assert r1 == r2
        client = b._get_client()
        body = client.get_object(Bucket="texts", Key=f"{'e' * 64}.txt")["Body"].read().decode()
        assert body == "v1"
