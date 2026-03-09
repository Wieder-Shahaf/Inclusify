"""PDF upload endpoint with Docling-based text extraction.

Replaces PyMuPDF with Docling for superior layout preservation in academic papers.
Uses subprocess isolation to protect the API server from memory exhaustion.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.modules.ingestion.service import parse_pdf_async
from app.modules.ingestion.schemas import UploadResponse
from app.auth.users import current_active_user
from app.db.models import User

router = APIRouter()

# 50MB size limit (prevent DoS)
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(current_active_user)
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
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    file_bytes = await file.read()

    # Enforce size limit
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (50MB limit)")

    result = await parse_pdf_async(file_bytes, timeout=60)

    if "error" in result:
        # Return specific error messages per CONTEXT.md decision
        raise HTTPException(status_code=400, detail=result["error"])

    return UploadResponse(
        filename=file.filename or "unknown.pdf",
        content_type=file.content_type,
        page_count=result["page_count"],
        text_preview=result["text"][:500] + "..." if len(result["text"]) > 500 else result["text"],
        full_text=result["text"],
        full_text_length=len(result["text"])
    )
