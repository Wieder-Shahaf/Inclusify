"""S3-compatible object storage client (Cloudflare R2 in prod, MinIO in dev).

Replaces the Azure Blob client (docs/STACK-A-MIGRATION.md §2.1). boto3 is sync,
so calls run in a thread executor to avoid blocking the async FastAPI endpoints.

Storage refs are emitted as `blob://<bucket>/<key>` — an opaque, stable format
kept identical across the Azure→R2 migration, so existing DB refs need no
rewriting (nothing parses them beyond equality).
"""
import asyncio
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _s3_enabled() -> bool:
    """Storage is active only when credentials are configured."""
    return bool(settings.S3_ACCESS_KEY_ID and settings.S3_SECRET_ACCESS_KEY)


def _get_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,  # None => AWS default endpoint
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        # path-style addressing works for both MinIO and R2; sigv4 is required by R2.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _object_exists(client, key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        client.head_object(Bucket=settings.S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False


def _ensure_bucket_sync() -> None:
    from botocore.exceptions import ClientError

    client = _get_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
        logger.info("S3 bucket ready: %s", settings.S3_BUCKET)
    except ClientError:
        try:
            client.create_bucket(Bucket=settings.S3_BUCKET)
            logger.info("S3 bucket created: %s", settings.S3_BUCKET)
        except ClientError as e:
            # R2 buckets are usually pre-provisioned; a create failure here is
            # non-fatal as long as the bucket exists.
            logger.info("S3 bucket create skipped for %s: %s", settings.S3_BUCKET, e)


async def ensure_container() -> None:
    if not _s3_enabled():
        logger.warning("S3 credentials not set — blob storage disabled")
        return
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _ensure_bucket_sync)
    except Exception as e:
        logger.warning("Blob storage init failed: %s", e)


def _upload_text_sync(sha256: str, text: str) -> str:
    client = _get_client()
    key = f"{sha256}.txt"
    # Keys are content-addressed by sha256, so an existing object is identical —
    # skip the re-upload (mirrors the old overwrite=False behaviour).
    if _object_exists(client, key):
        logger.debug("Text object already exists, skipping upload: %s", key)
    else:
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=text.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        logger.info("Text uploaded to S3: %s chars=%d", key, len(text))
    return f"blob://{settings.S3_BUCKET}/{key}"


async def upload_text(sha256: str, text: str) -> Optional[str]:
    if not _s3_enabled():
        return None
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _upload_text_sync, sha256, text)
    except Exception as e:
        logger.warning("Blob upload failed for %s: %s", sha256, e)
        return None


def _upload_file_sync(sha256: str, filename: str, data: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    client = _get_client()
    key = f"files/{sha256}.{ext}"
    if _object_exists(client, key):
        logger.debug("File object already exists, skipping upload: %s", key)
    else:
        client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data)
        logger.info("File uploaded to S3: %s size_bytes=%d", key, len(data))
    return f"blob://{settings.S3_BUCKET}/{key}"


async def upload_file_bytes(sha256: str, filename: str, data: bytes) -> Optional[str]:
    if not _s3_enabled():
        return None
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _upload_file_sync, sha256, filename, data)
    except Exception as e:
        logger.warning("Blob file upload failed for %s: %s", sha256, e)
        return None


def _report_key(run_id: str) -> str:
    return f"reports/{run_id}.pdf"


def _upload_report_sync(run_id: str, data: bytes) -> str:
    client = _get_client()
    key = _report_key(run_id)
    # Overwrite allowed: re-uploading a report for the same run replaces it.
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=data,
        ContentType="application/pdf",
    )
    logger.info("Report uploaded to S3: %s size_bytes=%d", key, len(data))
    return f"blob://{settings.S3_BUCKET}/{key}"


async def upload_report(run_id: str, data: bytes) -> Optional[str]:
    if not _s3_enabled():
        return None
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _upload_report_sync, run_id, data)
    except Exception as e:
        logger.warning("Report upload failed for run %s: %s", run_id, e)
        return None


def _download_report_sync(run_id: str) -> Optional[bytes]:
    from botocore.exceptions import ClientError

    client = _get_client()
    try:
        obj = client.get_object(Bucket=settings.S3_BUCKET, Key=_report_key(run_id))
        return obj["Body"].read()
    except ClientError:
        return None


async def download_report(run_id: str) -> Optional[bytes]:
    if not _s3_enabled():
        return None
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _download_report_sync, run_id)
    except Exception as e:
        logger.warning("Report download failed for run %s: %s", run_id, e)
        return None
