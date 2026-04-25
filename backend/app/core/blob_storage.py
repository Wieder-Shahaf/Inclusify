"""Azure Blob Storage client (sync, run in executor for async endpoints)."""
import asyncio
import logging
from typing import Optional

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

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
    try:
        blob.upload_blob(text.encode("utf-8"), overwrite=False)
        logger.info("Text uploaded to blob: %s chars=%d", blob_name, len(text))
    except ResourceExistsError:
        logger.debug("Text blob already exists, skipping upload: %s", blob_name)
    except ResourceNotFoundError:
        logger.warning("Container missing — recreating and retrying: %s", settings.AZURE_STORAGE_CONTAINER)
        _ensure_container_sync()
        blob.upload_blob(text.encode("utf-8"), overwrite=False)
        logger.info("Text uploaded to blob (after container recreate): %s", blob_name)
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


def _upload_file_sync(sha256: str, filename: str, data: bytes) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    client = _get_client()
    blob_name = f"files/{sha256}.{ext}"
    blob = client.get_blob_client(container=settings.AZURE_STORAGE_CONTAINER, blob=blob_name)
    try:
        blob.upload_blob(data, overwrite=False)
        logger.info("File uploaded to blob: %s size_bytes=%d", blob_name, len(data))
    except ResourceExistsError:
        logger.debug("File blob already exists, skipping upload: %s", blob_name)
    except ResourceNotFoundError:
        logger.warning("Container missing — recreating and retrying: %s", settings.AZURE_STORAGE_CONTAINER)
        _ensure_container_sync()
        blob.upload_blob(data, overwrite=False)
        logger.info("File uploaded to blob (after container recreate): %s size_bytes=%d", blob_name, len(data))
    return f"blob://{settings.AZURE_STORAGE_CONTAINER}/{blob_name}"


async def upload_file_bytes(sha256: str, filename: str, data: bytes) -> Optional[str]:
    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        return None
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _upload_file_sync, sha256, filename, data)
    except Exception as e:
        logger.warning("Blob file upload failed for %s: %s", sha256, e)
        return None
