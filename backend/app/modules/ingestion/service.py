"""Docling-based PDF parsing service with pypdf fallback.

Runs Docling in-process with OCR disabled (academic PDFs have text layers).
Enforces 50-page limit. No subprocess needed — saves memory in containers.
Falls back to pypdf extraction when Docling is unavailable (e.g. missing
or incompatible PyTorch in local dev; production Azure VM has PyTorch >= 2.4).
"""

import asyncio
import logging
import os
import tempfile
import time

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

MAX_PAGES = 50

# Initialize Docling converter once at module level (reuse across requests)
_docling_converter = None
_docling_unavailable = False  # Set to True after first failed init (avoid retrying)


def _get_docling_converter():
    """Lazy-init Docling converter with OCR disabled. Returns None if unavailable."""
    global _docling_converter, _docling_unavailable
    if _docling_unavailable:
        return None
    if _docling_converter is None:
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.base_models import InputFormat

            pipeline_opts = PdfPipelineOptions()
            pipeline_opts.do_ocr = False  # Academic PDFs have text layers
            pipeline_opts.do_table_structure = True

            _docling_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts),
                }
            )
            logger.info("Docling converter initialized (OCR disabled)")
        except Exception as e:
            _docling_unavailable = True
            logger.warning(
                "Docling unavailable (PyTorch missing or incompatible — install torch>=2.4 for full layout parsing): %s",
                e,
            )
    return _docling_converter


def _extract_text_pypdf(file_path: str) -> str:
    """Extract plain text from a PDF using pypdf (fallback when Docling is unavailable)."""
    reader = PdfReader(file_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text.strip())
    return "\n\n".join(pages_text)


def _parse_pdf_sync(file_bytes: bytes, max_pages: int = MAX_PAGES) -> dict:
    """Parse PDF synchronously using Docling.

    Args:
        file_bytes: Raw PDF file bytes
        max_pages: Maximum allowed page count (default 50)

    Returns:
        dict with either:
        - {"text": str, "page_count": int} on success
        - {"error": str} on failure
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(file_bytes)
        temp_path = f.name

    try:
        # Validate with pypdf first (lightweight)
        logger.info("pypdf validation started: size_bytes=%d", len(file_bytes))
        try:
            reader = PdfReader(temp_path)
            page_count = len(reader.pages)
            logger.info("pypdf validation succeeded: pages=%d", page_count)
        except PdfReadError as e:
            error_message = str(e).lower()
            if "password" in error_message or "encrypted" in error_message:
                logger.warning("pypdf validation failed: PDF is password-protected")
                return {"error": "PDF is password-protected"}
            logger.warning("pypdf validation failed: PDF appears corrupted error=%s", str(e))
            return {"error": "PDF appears corrupted"}
        except Exception as e:
            logger.warning("pypdf validation failed: unexpected error=%s", str(e))
            return {"error": "PDF appears corrupted"}

        if page_count > max_pages:
            logger.warning("Page limit exceeded: pages=%d limit=%d", page_count, max_pages)
            return {"error": f"Document exceeds {max_pages} page limit ({page_count} pages)"}

        # Process with Docling (OCR disabled, reuses converter); fall back to pypdf
        converter = _get_docling_converter()
        t0 = time.monotonic()
        if converter is not None:
            logger.info("Docling processing started: pages=%d", page_count)
            try:
                result = converter.convert(temp_path)
                text = result.document.export_to_markdown()
            except Exception as docling_err:
                logger.warning("Docling conversion failed, falling back to pypdf: %s", docling_err)
                text = _extract_text_pypdf(temp_path)
        else:
            logger.info("pypdf fallback extraction started: pages=%d", page_count)
            text = _extract_text_pypdf(temp_path)
        elapsed = time.monotonic() - t0
        logger.info("PDF extraction completed: pages=%d text_length=%d elapsed_s=%.2f", page_count, len(text), elapsed)

        return {"text": text, "page_count": page_count}

    except Exception as e:
        error_message = str(e).lower()
        if "password" in error_message or "encrypted" in error_message:
            logger.error("PDF processing failed: password-protected", exc_info=True)
            return {"error": "PDF is password-protected"}
        elif "corrupt" in error_message or "invalid" in error_message or "malformed" in error_message:
            logger.error("PDF processing failed: corrupted", exc_info=True)
            return {"error": "PDF appears corrupted"}
        logger.error("PDF processing failed: %s", str(e), exc_info=True)
        return {"error": f"Failed to process PDF: {str(e)}"}
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


async def parse_pdf_async(file_bytes: bytes) -> dict:
    """Async wrapper — runs Docling in a thread (not subprocess).

    No timeout enforced — analysis runs to completion.

    Args:
        file_bytes: Raw PDF file bytes

    Returns:
        dict with either:
        - {"text": str, "page_count": int} on success
        - {"error": str} on failure
    """
    logger.info("Async PDF parsing started: size_bytes=%d", len(file_bytes))
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _parse_pdf_sync, file_bytes)
