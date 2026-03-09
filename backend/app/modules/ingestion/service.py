"""Docling-based PDF parsing service with subprocess isolation.

Runs Docling in a subprocess to protect the API server from memory exhaustion
on large documents. Enforces 50-page limit and 60-second timeout.
"""

import asyncio
from concurrent.futures import ProcessPoolExecutor
from functools import partial

MAX_PAGES = 50
TIMEOUT_SECONDS = 60


def _parse_pdf_sync(file_bytes: bytes, max_pages: int = MAX_PAGES) -> dict:
    """Synchronous PDF parsing function run in subprocess.

    Imports Docling inside this function to isolate memory per request.
    The subprocess terminates after processing, releasing all memory.

    Args:
        file_bytes: Raw PDF file bytes
        max_pages: Maximum allowed page count (default 50)

    Returns:
        dict with either:
        - {"text": str, "page_count": int} on success
        - {"error": str} on failure
    """
    import tempfile
    import os

    # Write bytes to temp file (Docling needs file path)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(file_bytes)
        temp_path = f.name

    try:
        # Check page count first with pypdf (lightweight)
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(temp_path)
            page_count = len(reader.pages)
        except PdfReadError as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypted" in error_msg:
                return {"error": "PDF is password-protected"}
            return {"error": "PDF appears corrupted"}
        except Exception:
            return {"error": "PDF appears corrupted"}

        if page_count > max_pages:
            return {"error": f"Document exceeds {max_pages} page limit ({page_count} pages)"}

        # Process with Docling for layout preservation
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(temp_path)

        return {
            "text": result.document.export_to_markdown(),
            "page_count": page_count,
        }
    except Exception as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypted" in error_msg:
            return {"error": "PDF is password-protected"}
        elif "corrupt" in error_msg or "invalid" in error_msg or "malformed" in error_msg:
            return {"error": "PDF appears corrupted"}
        return {"error": f"Failed to process PDF: {str(e)}"}
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


async def parse_pdf_async(file_bytes: bytes, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Async wrapper with timeout - runs Docling in subprocess.

    Args:
        file_bytes: Raw PDF file bytes
        timeout: Maximum processing time in seconds (default 60)

    Returns:
        dict with either:
        - {"text": str, "page_count": int} on success
        - {"error": str} on failure or timeout
    """
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=1) as executor:
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, partial(_parse_pdf_sync, file_bytes)),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return {"error": f"Document processing timed out ({timeout}s limit)"}
