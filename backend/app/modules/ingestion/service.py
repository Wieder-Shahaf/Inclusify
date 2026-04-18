import asyncio
import logging
import os
import tempfile
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Raised to 100 — T4 handles up to ~100 pages within the 60s timeout at current load
MAX_PAGES = 100
_docling_converter = None

def _get_docling_converter():
    global _docling_converter
    if _docling_converter is None:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.datamodel.base_models import InputFormat

        pipeline_opts = PdfPipelineOptions()
        pipeline_opts.do_ocr = False  
        pipeline_opts.do_table_structure = True

        _docling_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts),
            }
        )
        logger.info("Docling converter initialized")
    return _docling_converter

def _parse_document_sync(file_bytes: bytes, filename: str, max_pages: int = MAX_PAGES) -> dict:
    ext = os.path.splitext(filename)[1].lower() or ".pdf"
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    logger.info("Extraction started: filename=%s ext=%s size_bytes=%d", filename, ext, len(file_bytes))

    try:
        with os.fdopen(temp_fd, 'wb') as f:
            f.write(file_bytes)


        page_count = 0
        pdf_title = None
        pdf_author = None

        # TXT passthrough — Docling adds no value for plain text and often
        # introduces spurious layout artifacts, so decode the bytes directly.
        if ext == ".txt":
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = file_bytes.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = file_bytes.decode("latin-1", errors="replace")
            has_hebrew = any('\u0590' <= c <= '\u05FF' for c in text[:500])
            detected = "he" if has_hebrew else "en"
            logger.info("Extraction completed (TXT passthrough): filename=%s detected_language=%s text_length=%d", filename, detected, len(text))
            return {
                "text": text,
                "page_count": 1,
                "title": None,
                "author": None,
                "detected_language": detected,
            }

        if ext == ".pdf":
            try:
                reader = PdfReader(temp_path)
                page_count = len(reader.pages)
                logger.info("PDF page check: filename=%s pages=%d max_pages=%d", filename, page_count, max_pages)
                if page_count > max_pages:
                    logger.warning("PDF rejected: page limit exceeded filename=%s pages=%d limit=%d", filename, page_count, max_pages)
                    return {"error": f"Document exceeds {max_pages} page limit ({page_count} pages)"}

                if reader.metadata:
                    if reader.metadata.title:
                        pdf_title = reader.metadata.title
                    if reader.metadata.author:
                        pdf_author = reader.metadata.author
            except Exception:
                logger.error("PDF corrupted: filename=%s", filename)
                return {"error": "PDF appears corrupted"}


        import time as _time
        _t0 = _time.monotonic()
        logger.info("Docling conversion started: filename=%s ext=%s", filename, ext)
        converter = _get_docling_converter()
        result = converter.convert(temp_path)
        logger.info("Docling conversion completed: filename=%s elapsed_s=%.3f", filename, _time.monotonic() - _t0)
        doc_dict = result.document.export_to_dict()
        items = doc_dict.get("texts", [])


        meta = getattr(result.document, 'metadata', None)
        title = getattr(meta, 'title', None) or pdf_title
        author = getattr(meta, 'author', None) or pdf_author


        meaningful_items = [item for item in items if item.get('label') not in ['page_header', 'page_footer']]
        first_few_items = meaningful_items[:20]

        title_index = -1
        if not title:

            for i, item in enumerate(first_few_items):
                if item.get('label') == 'title':
                    title = item.get('text', '')
                    title_index = i
                    break
            

            if not title:
                noise = ["university", "college", "school of", "digitalcommons", "journal", "abstract", "published", "אוניברסיטת", "אוניברסיטה", "מכללת", "מכללה", "בית ספר", "פקולטה", "מחלקה", "תקציר", "פורסם"]
                for i, item in enumerate(first_few_items):
                    text_val = item.get('text', '')
                    text_lower = text_val.lower()

                    if not any(n in text_lower for n in noise) and 10 < len(text_val) < 200:
                        title = text_val.strip()
                        title_index = i
                        break

        if title and title_index == -1:
            for i, item in enumerate(first_few_items):

                if title[:20].lower() in item.get('text', '').lower():
                    title_index = i
                    break

        if not author:

            for item in first_few_items:
                text_val = item.get('text', '').strip()
                lower_text = text_val.lower()
                prefixes = {"by ": 3, "מאת ": 4, "מאת:": 4, "על ידי ": 7, "נכתב עי ": 9, "נכתב על ידי ": 12}
                found_author = False
                for prefix, length in prefixes.items():
                    if lower_text.startswith(prefix):
                        author = text_val[length:].strip()
                        found_author = True
                        break
                if found_author:
                    break
            

            if not author and title_index != -1:
                for i in range(title_index + 1, min(title_index + 4, len(first_few_items))):
                    next_item = first_few_items[i]
                    text_val = next_item.get('text', '').strip()
                    text_lower = text_val.lower()
                    

                    if any(n in text_lower for n in ["abstract", "introduction", "university", "department", "email", "תקציר", "מבוא", "אוניברסיטה", "מחלקה", "דוא\"ל", "אימייל", "הקדמה", "פקולטה"]):
                        continue
                        

                    if 3 < len(text_val) < 80:
                        author = text_val
                        break


        full_markdown = result.document.export_to_markdown()
        has_hebrew = any('\u0590' <= c <= '\u05FF' for c in full_markdown[:500])
        detected_lang = "he" if has_hebrew else "en"
        final_pages = len(result.document.pages) if hasattr(result.document, 'pages') else page_count
        logger.info(
            "Extraction completed: filename=%s pages=%d text_length=%d detected_language=%s title=%s author=%s",
            filename, final_pages, len(full_markdown), detected_lang,
            repr(title[:50]) if title else None,
            repr(author[:50]) if author else None,
        )

        return {
            "text": full_markdown,
            "page_count": final_pages,
            "title": title,
            "author": author,
            "detected_language": detected_lang
        }
    except Exception as e:
        logger.error("Processing failed: %s", str(e), exc_info=True)
        return {"error": "Failed to process document. Please check the file and try again."}
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError as e:
                logger.warning(f"Failed to delete temp file: {e}")

async def parse_document_async(file_bytes: bytes, filename: str) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _parse_document_sync, file_bytes, filename)


async def warm_up_docling() -> None:
    """Pre-load Docling model weights at startup so the first upload is not slow."""
    loop = asyncio.get_running_loop()
    logger.info("Docling warm-up started — loading model weights")
    await loop.run_in_executor(None, _get_docling_converter)
    logger.info("Docling warm-up complete")