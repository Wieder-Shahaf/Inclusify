"""
Unit tests for CallMetrics flow through HybridDetector.analyze().

Verifies that:
- analyze() returns a 3-tuple (issues, mode, call_metrics)
- call_metrics reflects LLM call outcomes correctly
- total_sentences is set from the sentence splitter result
- mode is determined correctly from success/failure counts
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.analysis.call_metrics import CallMetrics


def _make_vllm_client(result):
    """Return a mock VLLMClient whose analyze_sentence returns `result`.

    The mock also captures the `metrics` kwarg and calls record_call on it,
    mimicking the real instrumented behaviour.
    """
    client = MagicMock()

    async def fake_analyze_sentence(sentence, metrics=None):
        if metrics is not None:
            if result is not None:
                metrics.record_call(50.0, success=True)
            else:
                metrics.record_call(0.0, success=False, error_type="timeout")
        return result

    client.analyze_sentence = fake_analyze_sentence
    return client


class TestHybridDetectorReturnsMetrics:
    @pytest.mark.asyncio
    async def test_analyze_returns_three_tuple(self):
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = _make_vllm_client(result=None)  # LLM unavailable
        detector = HybridDetector(vllm_client=mock_client)

        result = await detector.analyze("Hello world.", language="en")

        assert isinstance(result, tuple)
        assert len(result) == 3
        issues, mode, metrics = result
        assert isinstance(metrics, CallMetrics)

    @pytest.mark.asyncio
    async def test_metrics_total_sentences_set(self):
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = _make_vllm_client(result=None)
        detector = HybridDetector(vllm_client=mock_client)

        text = "First sentence. Second sentence."
        _, _, metrics = await detector.analyze(text, language="en")

        assert metrics.total_sentences >= 1  # at least one sentence split

    @pytest.mark.asyncio
    async def test_llm_success_reflected_in_metrics(self):
        from app.modules.analysis.hybrid_detector import HybridDetector

        llm_result = {
            "category": "N/A",
            "severity": "Correct",
            "explanation": "Fine",
            "confidence": 0.95,
        }
        mock_client = _make_vllm_client(result=llm_result)
        detector = HybridDetector(vllm_client=mock_client)

        _, _, metrics = await detector.analyze("Only one sentence.", language="en")

        assert metrics.llm_calls >= 1
        assert metrics.llm_successes >= 1
        assert metrics.llm_errors == 0

    @pytest.mark.asyncio
    async def test_llm_failure_reflected_in_metrics(self):
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = _make_vllm_client(result=None)
        detector = HybridDetector(vllm_client=mock_client)

        _, _, metrics = await detector.analyze("Only one sentence.", language="en")

        assert metrics.llm_calls >= 1
        assert metrics.llm_errors >= 1
        assert metrics.llm_successes == 0


class TestHybridDetectorMode:
    @pytest.mark.asyncio
    async def test_mode_rules_only_when_llm_all_fail(self):
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = _make_vllm_client(result=None)
        detector = HybridDetector(vllm_client=mock_client)

        _, mode, _ = await detector.analyze("Some text.", language="en")
        assert mode == "rules_only"

    @pytest.mark.asyncio
    async def test_mode_llm_when_all_succeed(self):
        from app.modules.analysis.hybrid_detector import HybridDetector

        llm_result = {"category": "N/A", "severity": "Correct", "explanation": "OK", "confidence": None}
        mock_client = _make_vllm_client(result=llm_result)
        detector = HybridDetector(vllm_client=mock_client)

        _, mode, _ = await detector.analyze("Some text.", language="en")
        assert mode == "llm"

    @pytest.mark.asyncio
    async def test_empty_text_returns_rules_only_mode(self):
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = _make_vllm_client(result=None)
        detector = HybridDetector(vllm_client=mock_client)

        issues, mode, metrics = await detector.analyze("", language="en")
        assert mode == "rules_only"
        assert metrics.total_sentences == 0
        assert metrics.llm_calls == 0
