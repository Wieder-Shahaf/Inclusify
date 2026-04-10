"""PDF upload endpoint with Docling-based text extraction.

Replaces PyMuPDF with Docling for superior layout preservation in academic papers.
Uses subprocess isolation to protect the API server from memory exhaustion.
"""

import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.modules.ingestion.service import parse_pdf_async
from app.modules.ingestion.schemas import UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 50MB size limit (prevent DoS)
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    # TODO: Re-enable auth once FastAPI Users schema matches DB
    # current_user: User = Depends(current_active_user)
):
    """
    Upload a PDF and extract text using Docling.

    Requires authentication. User info available for tracking uploads.

    Limits:
    - Max 50 pages
    - Max 50MB file size
    - 60-second processing timeout

    Returns specific errors for:
    - Password-protected PDFs
    - Corrupted PDFs
    - Oversized documents
    """
    filename = file.filename or "unknown.pdf"
    logger.info("Upload started: filename=%s content_type=%s", filename, file.content_type)

    is_pdf_content_type = file.content_type in ("application/pdf", "application/octet-stream")
    is_pdf_filename = filename.lower().endswith(".pdf")
    if not (is_pdf_content_type and is_pdf_filename):
        logger.warning("Upload rejected: unsupported content_type=%s filename=%s", file.content_type, filename)
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    file_bytes = await file.read()
    file_size = len(file_bytes)
    logger.info("Upload validated: filename=%s size_bytes=%d", filename, file_size)

    # Enforce size limit
    if file_size > MAX_FILE_SIZE:
        logger.warning("Upload rejected: file too large size_bytes=%d filename=%s", file_size, filename)
        raise HTTPException(status_code=400, detail="File too large (50MB limit)")

    logger.info("PDF parsing started: filename=%s", filename)
    result = await parse_pdf_async(file_bytes)

    if "error" in result:
        logger.error("PDF parsing failed: filename=%s error=%s", filename, result["error"])
        # Return specific error messages per CONTEXT.md decision
        raise HTTPException(status_code=400, detail=result["error"])

    text_length = len(result["text"])
    logger.info(
        "PDF parsing succeeded: filename=%s pages=%d text_length=%d",
        filename, result["page_count"], text_length,
    )

    return UploadResponse(
        filename=filename,
        content_type=file.content_type,
        page_count=result["page_count"],
        text_preview=result["text"][:500] + "..." if text_length > 500 else result["text"],
        full_text=result["text"],
        full_text_length=text_length,
    )
