"""
Tests for hybrid detection logic.
Tests cover overlap calculation, result merging, and HybridDetector orchestration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.analysis.router import Issue


class TestOverlapCalculation:
    """Tests for overlap calculation between issues."""

    def test_calculate_overlap_full(self):
        """Full overlap returns 1.0."""
        from app.modules.analysis.hybrid_detector import calculate_overlap

        # Two issues at exact same span
        issue1 = Issue(
            flagged_text="homosexual",
            severity="outdated",
            type="Outdated Terminology",
            description="Test",
            start=10,
            end=20
        )
        issue2 = Issue(
            flagged_text="homosexual",
            severity="biased",
            type="Different Type",
            description="Test",
            start=10,
            end=20
        )

        assert calculate_overlap(issue1, issue2) == 1.0

    def test_calculate_overlap_partial(self):
        """Partial overlap calculated correctly."""
        from app.modules.analysis.hybrid_detector import calculate_overlap

        # 50% overlap: issue1 spans 10-20, issue2 spans 15-25
        issue1 = Issue(
            flagged_text="first",
            severity="outdated",
            type="Type",
            description="Test",
            start=10,
            end=20
        )
        issue2 = Issue(
            flagged_text="second",
            severity="biased",
            type="Type",
            description="Test",
            start=15,
            end=25
        )

        overlap = calculate_overlap(issue1, issue2)
        # Overlap: 15-20 = 5 characters
        # Min length: min(10, 10) = 10
        # Ratio: 5/10 = 0.5
        assert overlap == 0.5

    def test_calculate_overlap_none(self):
        """No overlap returns 0.0."""
        from app.modules.analysis.hybrid_detector import calculate_overlap

        issue1 = Issue(
            flagged_text="first",
            severity="outdated",
            type="Type",
            description="Test",
            start=0,
            end=10
        )
        issue2 = Issue(
            flagged_text="second",
            severity="biased",
            type="Type",
            description="Test",
            start=20,
            end=30
        )

        assert calculate_overlap(issue1, issue2) == 0.0


class TestMergeResults:
    """Tests for merging LLM and rule-based results."""

    def test_merge_results_prefers_llm(self):
        """LLM issue kept, overlapping rule issue dropped."""
        from app.modules.analysis.hybrid_detector import merge_results

        llm_issue = Issue(
            flagged_text="homosexual",
            severity="biased",
            type="LLM Detected",
            description="LLM analysis",
            start=10,
            end=20
        )
        rule_issue = Issue(
            flagged_text="homosexual",
            severity="outdated",
            type="Rule Detected",
            description="Rule analysis",
            start=10,
            end=20
        )

        result = merge_results([llm_issue], [rule_issue])

        assert len(result) == 1
        assert result[0].type == "LLM Detected"

    def test_merge_results_adds_non_overlapping(self):
        """Non-overlapping rule issues added."""
        from app.modules.analysis.hybrid_detector import merge_results

        llm_issue = Issue(
            flagged_text="homosexual",
            severity="biased",
            type="LLM Detected",
            description="LLM analysis",
            start=0,
            end=10
        )
        rule_issue = Issue(
            flagged_text="transsexual",
            severity="outdated",
            type="Rule Detected",
            description="Rule analysis",
            start=50,
            end=60
        )

        result = merge_results([llm_issue], [rule_issue])

        assert len(result) == 2

    def test_merge_results_sorted_by_position(self):
        """Issues sorted by start position."""
        from app.modules.analysis.hybrid_detector import merge_results

        # LLM issue at position 50
        llm_issue = Issue(
            flagged_text="homosexual",
            severity="biased",
            type="LLM",
            description="Test",
            start=50,
            end=60
        )
        # Rule issue at position 10 (earlier)
        rule_issue = Issue(
            flagged_text="transsexual",
            severity="outdated",
            type="Rule",
            description="Test",
            start=10,
            end=20
        )

        result = merge_results([llm_issue], [rule_issue])

        assert len(result) == 2
        assert result[0].start == 10  # Rule issue first
        assert result[1].start == 50  # LLM issue second


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
            "explanation": "Test explanation"
        })

        detector = HybridDetector(vllm_client=mock_client)
        issues, mode = await detector.analyze("This is a test sentence. Another sentence.")

        assert mode == "llm"

    @pytest.mark.asyncio
    async def test_hybrid_detector_fallback_mode(self):
        """All LLM failure -> mode='rules_only'."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = MagicMock()
        # LLM returns None (failure)
        mock_client.analyze_sentence = AsyncMock(return_value=None)

        detector = HybridDetector(vllm_client=mock_client)
        issues, mode = await detector.analyze("The homosexual lifestyle is outdated terminology.")

        assert mode == "rules_only"

    @pytest.mark.asyncio
    async def test_hybrid_detector_hybrid_mode(self):
        """Partial LLM success -> mode='hybrid'."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        call_count = 0

        async def mock_analyze(sentence):
            nonlocal call_count
            call_count += 1
            # First call succeeds, second fails
            if call_count == 1:
                return {
                    "category": "Pathologizing",
                    "severity": "Biased",
                    "explanation": "Test"
                }
            return None

        mock_client = MagicMock()
        mock_client.analyze_sentence = mock_analyze

        detector = HybridDetector(vllm_client=mock_client)
        # Two sentences: one succeeds with LLM, one fails
        issues, mode = await detector.analyze("First sentence. Second sentence with homosexual.")

        assert mode == "hybrid"

    @pytest.mark.asyncio
    async def test_hybrid_detector_language_detection(self):
        """Auto language detection for Hebrew vs English."""
        from app.modules.analysis.hybrid_detector import HybridDetector

        mock_client = MagicMock()
        mock_client.analyze_sentence = AsyncMock(return_value=None)

        detector = HybridDetector(vllm_client=mock_client)

        # Hebrew text
        _, mode = await detector.analyze("זה משפט בעברית.", language="auto")
        # Should detect Hebrew and process accordingly
        assert mode == "rules_only"  # Because LLM returns None

        # English text
        _, mode = await detector.analyze("This is English.", language="auto")
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
