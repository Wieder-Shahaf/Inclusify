"""Tests for the BLOCK_OCR_DOCUMENTS guard: text-layer detection."""
from app.modules.ingestion.service import _pdf_has_text_layer, _ocr_blocked


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakeReader:
    def __init__(self, texts):
        self.pages = [_FakePage(t) for t in texts]


def test_scanned_pdf_has_no_text_layer():
    # Scanned pages return empty / whitespace / None → needs OCR.
    assert _pdf_has_text_layer(_FakeReader(["  ", "", None])) is False


def test_text_pdf_has_text_layer():
    assert _pdf_has_text_layer(_FakeReader(["This page has a real, extractable text layer."])) is True


def test_text_accumulates_across_pages():
    # No single page clears the threshold, but the sum does.
    assert _pdf_has_text_layer(_FakeReader(["ab", "cde", "fghijklmnopqrstuvwxyz"])) is True


def test_extract_text_exception_is_ignored():
    class _BoomPage:
        def extract_text(self):
            raise ValueError("boom")
    r = _FakeReader([])
    r.pages = [_BoomPage(), _FakePage("enough real text to pass the threshold here")]
    assert _pdf_has_text_layer(r) is True


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("BLOCK_OCR_DOCUMENTS", raising=False)
    assert _ocr_blocked() is False
    monkeypatch.setenv("BLOCK_OCR_DOCUMENTS", "true")
    assert _ocr_blocked() is True
