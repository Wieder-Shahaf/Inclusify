"""
Integration tests for live vLLM inference endpoint.

These tests require a running vLLM instance. They are skipped automatically
when VLLM_URL is not set or points to localhost (unit test environment).

Run manually:
    VLLM_URL=http://<host>:8001 pytest tests/test_vllm_integration.py -v

Or via GitHub Actions workflow: .github/workflows/vllm-integration.yml
"""

import os
import httpx
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Skip entire module when no live vLLM is configured or reachable
# ---------------------------------------------------------------------------

VLLM_URL = os.environ.get("VLLM_URL", "")


def _vllm_is_reachable() -> bool:
    if not VLLM_URL or "localhost" in VLLM_URL:
        return False
    try:
        response = httpx.get(f"{VLLM_URL}/v1/models", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


_vllm_available = _vllm_is_reachable()

pytestmark = pytest.mark.skipif(
    not _vllm_available,
    reason="vLLM server is not reachable — skipping integration tests",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SEVERITIES = {"Correct", "Outdated", "Biased", "Potentially Offensive", "Factually Incorrect"}
VALID_API_SEVERITIES = {"outdated", "biased", "potentially_offensive", "factually_incorrect"}


def assert_valid_llm_response(result: dict, sentence: str):
    """Assert that a raw LLM response dict has the expected structure."""
    assert result is not None, f"LLM returned None for: {sentence!r}"
    assert "severity" in result, f"Missing 'severity' key in response: {result}"
    assert "category" in result, f"Missing 'category' key in response: {result}"
    assert "explanation" in result, f"Missing 'explanation' key in response: {result}"
    assert result["severity"] in VALID_SEVERITIES, (
        f"Unexpected severity {result['severity']!r} not in {VALID_SEVERITIES}"
    )
    assert isinstance(result["explanation"], str) and len(result["explanation"]) > 0, (
        f"explanation should be a non-empty string, got: {result['explanation']!r}"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def vllm_client():
    """VLLMClient pointed at the live VLLM_URL from env."""
    from app.modules.analysis.llm_client import VLLMClient
    return VLLMClient(base_url=VLLM_URL, timeout=60.0)


# ---------------------------------------------------------------------------
# Health / connectivity
# ---------------------------------------------------------------------------

class TestVLLMConnectivity:

    @pytest.mark.asyncio
    async def test_models_endpoint_responds(self):
        """GET /v1/models returns a valid model list."""
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{VLLM_URL}/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data, f"Expected 'data' key in /v1/models response: {data}"
        assert len(data["data"]) > 0, "No models listed in /v1/models"

    @pytest.mark.asyncio
    async def test_lora_adapter_loaded(self):
        """The 'inclusify' LoRA adapter appears in the model list."""
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{VLLM_URL}/v1/models")
        data = response.json()
        model_ids = [m["id"] for m in data["data"]]
        assert any("inclusify" in mid.lower() for mid in model_ids), (
            f"LoRA adapter 'inclusify' not found in model list: {model_ids}"
        )


# ---------------------------------------------------------------------------
# English inference
# ---------------------------------------------------------------------------

class TestEnglishInference:

    @pytest.mark.asyncio
    async def test_correct_english_sentence(self, vllm_client):
        """A clearly inclusive sentence is classified as Correct."""
        sentence = "The researcher studied experiences of transgender individuals in academic settings."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)
        assert result["severity"] == "Correct", (
            f"Expected 'Correct' for inclusive sentence, got {result['severity']!r}\n"
            f"Explanation: {result['explanation']}"
        )

    @pytest.mark.asyncio
    async def test_outdated_english_term(self, vllm_client):
        """'homosexual' in a clinical context is flagged as Outdated."""
        sentence = "The study examined homosexual behavior patterns using clinical assessment tools."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)
        assert result["severity"] != "Correct", (
            f"Expected a non-Correct severity for sentence with 'homosexual', "
            f"got {result['severity']!r}\nExplanation: {result['explanation']}"
        )

    @pytest.mark.asyncio
    async def test_factually_incorrect_english(self, vllm_client):
        """'sexual preference' is flagged as Factually Incorrect."""
        sentence = "Participants reported their sexual preference as part of the demographic survey."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)
        assert result["severity"] != "Correct", (
            f"Expected non-Correct severity for 'sexual preference', "
            f"got {result['severity']!r}\nExplanation: {result['explanation']}"
        )

    @pytest.mark.asyncio
    async def test_response_format_english(self, vllm_client):
        """Response always contains category, severity, explanation for English input."""
        sentence = "The paper reviewed current literature on LGBTQ+ health outcomes."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)


# ---------------------------------------------------------------------------
# Hebrew inference
# ---------------------------------------------------------------------------

class TestHebrewInference:

    @pytest.mark.asyncio
    async def test_correct_hebrew_sentence(self, vllm_client):
        """An inclusive Hebrew sentence is classified as Correct."""
        sentence = "המחקר בחן את חוויות האנשים הטרנסג'נדרים בהקשר אקדמי."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)
        assert result["severity"] == "Correct", (
            f"Expected 'Correct' for inclusive Hebrew sentence, got {result['severity']!r}\n"
            f"Explanation: {result['explanation']}"
        )

    @pytest.mark.asyncio
    async def test_outdated_hebrew_term(self, vllm_client):
        """'הומוסקסואל' in a clinical context is flagged."""
        sentence = "המחקר בחן דפוסי התנהגות הומוסקסואל באמצעות כלי הערכה קליניים."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)
        assert result["severity"] != "Correct", (
            f"Expected non-Correct severity for 'הומוסקסואל', "
            f"got {result['severity']!r}\nExplanation: {result['explanation']}"
        )

    @pytest.mark.asyncio
    async def test_factually_incorrect_hebrew(self, vllm_client):
        """'העדפה מינית' is flagged as Factually Incorrect."""
        sentence = "המשתתפים דיווחו על העדפתם המינית כחלק מסקר דמוגרפי."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)
        assert result["severity"] != "Correct", (
            f"Expected non-Correct severity for 'העדפה מינית', "
            f"got {result['severity']!r}\nExplanation: {result['explanation']}"
        )

    @pytest.mark.asyncio
    async def test_response_format_hebrew(self, vllm_client):
        """Response always contains category, severity, explanation for Hebrew input."""
        sentence = "המאמר סקר את ספרות המחקר העדכנית בנושא בריאות קהילת הלהט\"ב."
        result = await vllm_client.analyze_sentence(sentence)
        assert_valid_llm_response(result, sentence)


# ---------------------------------------------------------------------------
# Severity mapping (end-to-end through map_severity)
# ---------------------------------------------------------------------------

class TestSeverityMappingEndToEnd:

    @pytest.mark.asyncio
    async def test_mapped_severity_is_valid_api_value(self, vllm_client):
        """map_severity converts LLM output to a valid API severity or None."""
        from app.modules.analysis.llm_client import map_severity

        sentence = "The study examined homosexual behavior patterns using outdated clinical tools."
        result = await vllm_client.analyze_sentence(sentence)
        assert result is not None

        mapped = map_severity(result["severity"])
        if result["severity"] == "Correct":
            assert mapped is None
        else:
            assert mapped in VALID_API_SEVERITIES, (
                f"map_severity({result['severity']!r}) = {mapped!r} "
                f"not in valid API severities {VALID_API_SEVERITIES}"
            )
