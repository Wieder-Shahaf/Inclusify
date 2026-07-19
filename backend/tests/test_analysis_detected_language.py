"""The /analyze response must report the detected language so the frontend can
render the downloaded report in the document's language (not the UI locale).

Two sources, both covered here:
  - upload path: the client sends detected_language (from extraction) → echoed back
  - paste path:  no detected_language sent → resolved from the text itself
"""

import pytest

from app.modules.analysis.call_metrics import CallMetrics


@pytest.fixture(autouse=True)
def _stub_detector(monkeypatch):
    """Skip real vLLM — return no issues so the endpoint just does language resolution."""
    async def fake_analyze(text, language="auto", chunks=None):
        return [], "llm", CallMetrics()

    monkeypatch.setattr(
        "app.modules.analysis.router._hybrid_detector.analyze", fake_analyze
    )


@pytest.mark.asyncio
async def test_echoes_client_detected_language(test_client):
    """Upload path: extraction's detected_language wins over auto-detection."""
    resp = await test_client.post(
        "/api/v1/analysis/analyze",
        json={"text": "This English text was extracted from a Hebrew-metadata file.",
              "detected_language": "he", "private_mode": True},
    )
    assert resp.status_code == 200
    assert resp.json()["detected_language"] == "he"


@pytest.mark.asyncio
async def test_falls_back_to_text_detection(test_client):
    """Paste path: no client value → language detected from the text."""
    resp = await test_client.post(
        "/api/v1/analysis/analyze",
        json={"text": "זהו טקסט בעברית לבדיקת זיהוי השפה של הדוח.", "private_mode": True},
    )
    assert resp.status_code == 200
    assert resp.json()["detected_language"] == "he"
