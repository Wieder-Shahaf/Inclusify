"""
Tests for LLM detection logic and HybridDetector orchestration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestHybridDetector:
    """Tests for HybridDetector orchestration."""

    @pytest.mark.asyncio
    async def test_hybrid_detector_llm_mode(self):
        """All LLM success -> mode='llm'."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = MagicMock()
        mock_client.analyze_sentence = AsyncMock(return_value={
            "category": "Pathologizing",
            "severity": "Biased",
            "explanation": "Test explanation",
            "suggestion": "Use affirming language instead.",
        })
        mock_client.get_suggestion = AsyncMock(return_value="Use affirming language instead.")

        detector = HybridDetector(vllm_client=mock_client)
        issues, mode, _ = await detector.analyze("This is a test sentence. Another sentence.")

        assert mode == "llm"

    @pytest.mark.asyncio
    async def test_hybrid_detector_fallback_mode(self):
        """All LLM failure -> mode='rules_only'."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = MagicMock()
        # LLM returns None (failure)
        mock_client.analyze_sentence = AsyncMock(return_value=None)

        detector = HybridDetector(vllm_client=mock_client)
        issues, mode, _ = await detector.analyze("The homosexual lifestyle is outdated terminology.")

        assert mode == "rules_only"

    @pytest.mark.asyncio
    async def test_hybrid_detector_hybrid_mode(self):
        """Partial LLM success -> mode='llm' (system is LLM-only, no hybrid mode)."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        call_count = 0

        async def mock_analyze(sentence, metrics=None):
            nonlocal call_count
            call_count += 1
            # First call succeeds, second fails
            if call_count == 1:
                if metrics is not None:
                    metrics.record_call(50.0, success=True)
                return {
                    "category": "Pathologizing",
                    "severity": "Biased",
                    "explanation": "Test"
                }
            if metrics is not None:
                metrics.record_call(0.0, success=False, error_type="timeout")
            return None

        mock_client = MagicMock()
        mock_client.analyze_sentence = mock_analyze
        mock_client.get_suggestion = AsyncMock(return_value="Use affirming language instead.")

        detector = HybridDetector(vllm_client=mock_client)
        # Two sentences: one succeeds with LLM, one fails
        issues, mode, _ = await detector.analyze("First sentence. Second sentence with homosexual.")

        assert mode == "llm"

    @pytest.mark.asyncio
    async def test_hybrid_detector_language_detection(self):
        """Auto language detection for Hebrew vs English."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = MagicMock()
        mock_client.analyze_sentence = AsyncMock(return_value=None)

        detector = HybridDetector(vllm_client=mock_client)

        # Hebrew text
        _, mode, _ = await detector.analyze("זה משפט בעברית.", language="auto")
        # Should detect Hebrew and process accordingly
        assert mode == "rules_only"  # Because LLM returns None

        # English text
        _, mode, _ = await detector.analyze("This is English.", language="auto")
        assert mode == "rules_only"


class TestAnalysisModeResponse:
    """Tests for analysis_mode in API response."""

    def test_analysis_response_includes_mode(self):
        """AnalysisResponse includes analysis_mode field."""
        from app.modules.analysis.router import AnalysisResponse

        response = AnalysisResponse(
            original_text="Test",
            analysis_status="Success",
            issues_found=[],
            analysis_mode="llm"
        )

        assert hasattr(response, "analysis_mode")
        assert response.analysis_mode == "llm"

    def test_analysis_mode_literal_values(self):
        """analysis_mode accepts all valid literal values."""
        from app.modules.analysis.router import AnalysisResponse

        for mode in ["llm", "hybrid", "rules_only"]:
            response = AnalysisResponse(
                original_text="Test",
                analysis_status="Success",
                issues_found=[],
                analysis_mode=mode
            )
            assert response.analysis_mode == mode
