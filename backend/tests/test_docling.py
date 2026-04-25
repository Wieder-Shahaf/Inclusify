import pytest
from unittest.mock import patch, MagicMock


class TestParseDocumentSync:
    """Tests for the synchronous document parsing function."""

    def test_page_limit_exceeded(self):
        """PDFs exceeding max_pages are rejected with a specific message."""
        from app.modules.ingestion.service import _parse_document_sync

        with patch('app.modules.ingestion.service.PdfReader') as mock_reader:
            mock_instance = MagicMock()
            mock_instance.pages = [MagicMock()] * 55
            mock_instance.metadata = None
            mock_reader.return_value = mock_instance

            result = _parse_document_sync(b"%PDF-1.4 fake", "test.pdf", max_pages=50)
            assert "error" in result
            assert "50 page limit" in result["error"]
            assert "55 pages" in result["error"]

    def test_password_protected_error(self):
        """Password-protected PDF returns a specific message."""
        from app.modules.ingestion.service import _parse_document_sync
        from pypdf.errors import PdfReadError

        with patch('app.modules.ingestion.service.PdfReader') as mock_reader:
            mock_reader.side_effect = PdfReadError("File is encrypted")

            result = _parse_document_sync(b"%PDF-1.4 fake", "test.pdf")
            assert result == {"error": "PDF is password-protected"}

    def test_corrupted_pdf_error(self):
        """Corrupted PDF returns a specific message."""
        from app.modules.ingestion.service import _parse_document_sync
        from pypdf.errors import PdfReadError

        with patch('app.modules.ingestion.service.PdfReader') as mock_reader:
            mock_reader.side_effect = PdfReadError("Invalid PDF structure")

            result = _parse_document_sync(b"not a pdf", "test.pdf")
            assert result == {"error": "PDF appears corrupted"}

    def test_valid_pdf_returns_text_and_page_count(self):
        """Valid PDF returns text and page_count."""
        from app.modules.ingestion.service import _parse_document_sync

        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [MagicMock()] * 5
        mock_reader_instance.metadata = None

        mock_converter_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.document.export_to_text.return_value = "Document Title\n\nSample text content."
        mock_result.document.export_to_dict.return_value = {"texts": []}
        mock_result.document.pages = {i: MagicMock() for i in range(1, 6)}
        mock_converter_instance.convert.return_value = mock_result

        mock_chunker_instance = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.text = "Sample text content."
        mock_chunker_instance.chunk.return_value = [mock_chunk]

        with patch('app.modules.ingestion.service.PdfReader', return_value=mock_reader_instance), \
             patch('app.modules.ingestion.service._get_docling_converter', return_value=mock_converter_instance), \
             patch('app.modules.ingestion.service._get_hybrid_chunker', return_value=mock_chunker_instance):
            result = _parse_document_sync(b"%PDF-1.4 fake", "test.pdf")
            assert "text" in result
            assert "page_count" in result
            assert result["page_count"] == 5
            assert "Sample text content" in result["text"]
            assert result["chunks"] == ["Sample text content."]


class TestTxtPassthrough:
    """TXT files decode directly without going through Docling."""

    def test_utf8_english_passthrough(self):
        from app.modules.ingestion.service import _parse_document_sync
        result = _parse_document_sync(b"Hello world, this is plain text.", "note.txt")
        assert result["text"] == "Hello world, this is plain text."
        assert result["page_count"] == 1
        assert result["detected_language"] == "en"
        assert result["title"] is None
        assert result["author"] is None

    def test_utf8_hebrew_detected(self):
        from app.modules.ingestion.service import _parse_document_sync
        result = _parse_document_sync("שלום עולם".encode("utf-8"), "note.txt")
        assert result["detected_language"] == "he"
        assert "שלום" in result["text"]

    def test_bom_utf8_decodes(self):
        from app.modules.ingestion.service import _parse_document_sync
        payload = "\ufeffplain text".encode("utf-8")
        result = _parse_document_sync(payload, "note.txt")
        assert "plain text" in result["text"]

    def test_docling_not_invoked_for_txt(self):
        from app.modules.ingestion.service import _parse_document_sync
        with patch('app.modules.ingestion.service._get_docling_converter') as mock_conv:
            _parse_document_sync(b"hi", "note.txt")
            mock_conv.assert_not_called()


class TestParseDocumentAsync:
    """Tests for the async document parsing wrapper."""

    @pytest.mark.asyncio
    async def test_calls_sync_in_executor(self):
        """Async wrapper delegates to sync function."""
        from app.modules.ingestion.service import parse_document_async

        mock_result = {"text": "test content", "page_count": 1}

        with patch('app.modules.ingestion.service._parse_document_sync', return_value=mock_result):
            result = await parse_document_async(b"%PDF-1.4 fake", "test.pdf")
            assert result == mock_result


class TestUploadEndpoint:
    """Integration tests for upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_unsupported_type_rejected(self, test_client):
        """Non-allowed content types are rejected."""
        from io import BytesIO

        response = await test_client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.bin", BytesIO(b"hello"), "application/octet-stream")}
        )
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_oversized_file_rejected(self, test_client):
        """Files over 50MB are rejected."""
        from io import BytesIO

        large_content = b"x" * (50 * 1024 * 1024 + 1)

        response = await test_client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
        )
        assert response.status_code == 400
        assert "50MB" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_valid_pdf_returns_response(self, test_client):
        """Valid PDF returns UploadResponse structure."""
        from io import BytesIO

        mock_result = {"text": "# Test\n\nDocument content", "page_count": 3}

        with patch('app.modules.ingestion.router.parse_document_async', return_value=mock_result):
            response = await test_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("test.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "test.pdf"
            assert data["page_count"] == 3
            assert "text_preview" in data
            assert "full_text_length" in data

    @pytest.mark.asyncio
    async def test_upload_page_limit_error(self, test_client):
        """>50 page PDF returns 400."""
        from io import BytesIO

        mock_result = {"error": "Document exceeds 50 page limit (100 pages)"}

        with patch('app.modules.ingestion.router.parse_document_async', return_value=mock_result):
            response = await test_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("large.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
            )
            assert response.status_code == 400
            assert "50 page limit" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_password_protected_error(self, test_client):
        """Password-protected PDF returns 400."""
        from io import BytesIO

        mock_result = {"error": "PDF is password-protected"}

        with patch('app.modules.ingestion.router.parse_document_async', return_value=mock_result):
            response = await test_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("secret.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
            )
            assert response.status_code == 400
            assert "password-protected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_corrupted_pdf_error(self, test_client):
        """Corrupted PDF returns 400."""
        from io import BytesIO

        mock_result = {"error": "PDF appears corrupted"}

        with patch('app.modules.ingestion.router.parse_document_async', return_value=mock_result):
            response = await test_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("bad.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
            )
            assert response.status_code == 400
            assert "corrupted" in response.json()["detail"]
