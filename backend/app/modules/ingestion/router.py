"""Document upload endpoint with Docling-based text extraction.

Supports PDF, DOCX, PPTX, and TXT formats.
Uses subprocess isolation to protect the API server from memory exhaustion.
"""

import asyncio
import hashlib
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.modules.ingestion.service import parse_document_async
from app.modules.ingestion.schemas import UploadResponse
from app.core.blob_storage import upload_file_bytes as _blob_upload_file

logger = logging.getLogger(__name__)

router = APIRouter()

# 50MB size limit (prevent DoS)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Limit concurrent Docling parses to prevent OOM and CPU starvation under load.
MAX_CONCURRENT_PARSES = 2
parse_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PARSES)

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # PPTX
    "text/plain" # TXT
}

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    # TODO: Re-enable auth once FastAPI Users schema matches DB
    # current_user: User = Depends(current_active_user)
):
    """
    Upload a document (PDF, DOCX, PPTX, TXT) and extract text using Docling.
    """
    filename = file.filename or "unknown.ext"
    logger.info("Upload started: filename=%s content_type=%s", filename, file.content_type)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning("Upload rejected: unsupported content_type=%s filename=%s", file.content_type, filename)
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, DOCX, PPTX, or TXT.")

    file_bytes = await file.read()
    file_size = len(file_bytes)
    logger.info("Upload validated: filename=%s size_bytes=%d", filename, file_size)

    # Enforce size limit
    if file_size > MAX_FILE_SIZE:
        logger.warning("Upload rejected: file too large size_bytes=%d filename=%s", file_size, filename)
        raise HTTPException(status_code=400, detail="File too large (50MB limit)")

    logger.info("Document parsing started: filename=%s", filename)

    async with parse_semaphore:
        result = await parse_document_async(file_bytes, filename)

    if "error" in result:
        logger.error("Document parsing failed: filename=%s error=%s", filename, result["error"])
        raise HTTPException(status_code=400, detail=result["error"])

    text_length = len(result["text"])
    logger.info(
        "Document parsing succeeded: filename=%s pages=%d text_length=%d",
        filename, result["page_count"], text_length,
    )

    file_sha256 = hashlib.sha256(file_bytes).hexdigest()
    file_storage_ref = await _blob_upload_file(file_sha256, filename, file_bytes)

    return UploadResponse(
        filename=filename,
        content_type=file.content_type,
        page_count=result["page_count"],
        text_preview=result["text"][:500] + "..." if text_length > 500 else result["text"],
        full_text=result["text"],
        full_text_length=text_length,
        title=result.get("title"),
        author=result.get("author"),
        detected_language=result.get("detected_language"),
        file_storage_ref=file_storage_ref,
        chunks=result.get("chunks"),
    )
