"""
Azure Blob Storage client for text storage.

Uses Azurite locally (via docker-compose) and Azure Blob Storage in production.
Switch is transparent — just change AZURE_STORAGE_CONNECTION_STRING env var.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _get_client():
    from azure.storage.blob.aio import BlobServiceClient
    return BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)


async def ensure_container() -> None:
    """Create blob container if it doesn't exist. Called at startup."""
    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not set — blob storage disabled")
        return
    try:
        async with await _get_client() as client:
            container = client.get_container_client(settings.AZURE_STORAGE_CONTAINER)
            if not await container.exists():
                await container.create_container()
                logger.info("Blob container created: %s", settings.AZURE_STORAGE_CONTAINER)
            else:
                logger.info("Blob container ready: %s", settings.AZURE_STORAGE_CONTAINER)
    except Exception as e:
        logger.warning("Blob storage init failed (storage disabled): %s", e)


async def upload_text(sha256: str, text: str) -> Optional[str]:
    """
    Upload text to blob storage. Returns blob URL/ref or None on failure.
    Idempotent — if blob exists, returns ref without re-uploading.
    """
    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        return None

    blob_name = f"{sha256}.txt"
    try:
        async with await _get_client() as client:
            blob = client.get_blob_client(
                container=settings.AZURE_STORAGE_CONTAINER,
                blob=blob_name,
            )
            if not await blob.exists():
                await blob.upload_blob(text.encode("utf-8"), overwrite=False)
                logger.info("Text uploaded to blob: %s chars=%d", blob_name, len(text))
            return f"blob://{settings.AZURE_STORAGE_CONTAINER}/{blob_name}"
    except Exception as e:
        logger.warning("Blob upload failed for %s: %s", blob_name, e)
        return None
