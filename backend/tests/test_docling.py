import pytest
from unittest.mock import patch, MagicMock


class TestParsePdfSync:
    """Tests for the synchronous PDF parsing function."""

    def test_page_limit_exceeded(self):
        """Test that >50 page PDFs are rejected with specific message."""
        from app.modules.ingestion.service import _parse_pdf_sync

        with patch('app.modules.ingestion.service.PdfReader') as mock_reader:
            mock_instance = MagicMock()
            mock_instance.pages = [MagicMock()] * 55  # 55 pages
            mock_reader.return_value = mock_instance

            result = _parse_pdf_sync(b"%PDF-1.4 fake")
            assert "error" in result
            assert "exceeds 50 page limit" in result["error"]
            assert "55 pages" in result["error"]

    def test_password_protected_error(self):
        """Test password-protected PDF returns specific message."""
        from app.modules.ingestion.service import _parse_pdf_sync
        from pypdf.errors import PdfReadError

        with patch('app.modules.ingestion.service.PdfReader') as mock_reader:
            mock_reader.side_effect = PdfReadError("File is encrypted")

            result = _parse_pdf_sync(b"%PDF-1.4 fake")
            assert result == {"error": "PDF is password-protected"}

    def test_corrupted_pdf_error(self):
        """Test corrupted PDF returns specific message."""
        from app.modules.ingestion.service import _parse_pdf_sync
        from pypdf.errors import PdfReadError

        with patch('app.modules.ingestion.service.PdfReader') as mock_reader:
            mock_reader.side_effect = PdfReadError("Invalid PDF structure")

            result = _parse_pdf_sync(b"not a pdf")
            assert result == {"error": "PDF appears corrupted"}

    def test_valid_pdf_returns_text_and_page_count(self):
        """Test valid PDF returns text and page_count."""
        from app.modules.ingestion.service import _parse_pdf_sync

        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [MagicMock()] * 5  # 5 pages

        mock_converter_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# Document Title\n\nSample text content."
        mock_converter_instance.convert.return_value = mock_result

        with patch('app.modules.ingestion.service.PdfReader', return_value=mock_reader_instance):
            with patch('app.modules.ingestion.service._get_docling_converter', return_value=mock_converter_instance):
                result = _parse_pdf_sync(b"%PDF-1.4 fake")
                assert "text" in result
                assert "page_count" in result
                assert result["page_count"] == 5
                assert "Sample text content" in result["text"]


class TestParsePdfAsync:
    """Tests for the async PDF parsing wrapper."""

    @pytest.mark.asyncio
    async def test_calls_sync_in_executor(self):
        """Test that async wrapper delegates to sync function."""
        from app.modules.ingestion.service import parse_pdf_async

        mock_result = {"text": "test content", "page_count": 1}

        with patch('app.modules.ingestion.service._parse_pdf_sync', return_value=mock_result):
            result = await parse_pdf_async(b"%PDF-1.4 fake")
            assert result == mock_result


class TestUploadEndpoint:
    """Integration tests for upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_non_pdf_rejected(self, test_client):
        """Test non-PDF files are rejected."""
        from io import BytesIO

        response = await test_client.post(
            "/api/v1/ingestion/upload",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")}
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_oversized_file_rejected(self, test_client):
        """Test files over 50MB are rejected."""
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
        """Test valid PDF returns UploadResponse structure."""
        from io import BytesIO

        mock_result = {"text": "# Test\n\nDocument content", "page_count": 3}

        with patch('app.modules.ingestion.router.parse_pdf_async', return_value=mock_result):
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
        """Test >50 page PDF returns 400."""
        from io import BytesIO

        mock_result = {"error": "Document exceeds 50 page limit (100 pages)"}

        with patch('app.modules.ingestion.router.parse_pdf_async', return_value=mock_result):
            response = await test_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("large.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
            )
            assert response.status_code == 400
            assert "50 page limit" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_password_protected_error(self, test_client):
        """Test password-protected PDF returns 400."""
        from io import BytesIO

        mock_result = {"error": "PDF is password-protected"}

        with patch('app.modules.ingestion.router.parse_pdf_async', return_value=mock_result):
            response = await test_client.post(
                "/api/v1/ingestion/upload",
                files={"file": ("secret.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
            )
            assert response.status_code == 400
            assert "password-protected" in response.json()["detail"]
