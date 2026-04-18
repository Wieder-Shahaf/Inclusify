"""Azure Blob Storage client (sync, run in executor for async endpoints)."""
import asyncio
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client():
    from azure.storage.blob import BlobServiceClient
    return BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)


def _ensure_container_sync() -> None:
    client = _get_client()
    container = client.get_container_client(settings.AZURE_STORAGE_CONTAINER)
    try:
        container.create_container()
        logger.info("Blob container created: %s", settings.AZURE_STORAGE_CONTAINER)
    except Exception:
        logger.info("Blob container ready: %s", settings.AZURE_STORAGE_CONTAINER)


async def ensure_container() -> None:
    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not set — blob storage disabled")
        return
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _ensure_container_sync)
    except Exception as e:
        logger.warning("Blob storage init failed: %s", e)


def _upload_text_sync(sha256: str, text: str) -> str:
    client = _get_client()
    blob_name = f"{sha256}.txt"
    blob = client.get_blob_client(container=settings.AZURE_STORAGE_CONTAINER, blob=blob_name)
    if not blob.exists():
        blob.upload_blob(text.encode("utf-8"), overwrite=False)
        logger.info("Text uploaded to blob: %s chars=%d", blob_name, len(text))
    return f"blob://{settings.AZURE_STORAGE_CONTAINER}/{blob_name}"


async def upload_text(sha256: str, text: str) -> Optional[str]:
    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        return None
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _upload_text_sync, sha256, text)
    except Exception as e:
        logger.warning("Blob upload failed for %s: %s", sha256, e)
        return None
