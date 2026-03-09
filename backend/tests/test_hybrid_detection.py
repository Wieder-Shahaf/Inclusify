"""
Test stubs for hybrid detection logic.
These tests will fail until Plan 03-03 implementation completes.
"""
import pytest


class TestOverlapCalculation:
    """Tests for overlap calculation between issues."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    def test_calculate_overlap_full(self):
        """Full overlap returns 1.0."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    def test_calculate_overlap_partial(self):
        """Partial overlap calculated correctly."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    def test_calculate_overlap_none(self):
        """No overlap returns 0.0."""
        pass


class TestMergeResults:
    """Tests for merging LLM and rule-based results."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    def test_merge_results_prefers_llm(self):
        """LLM issue kept, overlapping rule issue dropped."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    def test_merge_results_adds_non_overlapping(self):
        """Non-overlapping rule issues added."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    def test_merge_results_sorted_by_position(self):
        """Issues sorted by start position."""
        pass


class TestHybridDetector:
    """Tests for HybridDetector orchestration."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    @pytest.mark.asyncio
    async def test_hybrid_detector_llm_mode(self):
        """All LLM success -> mode='llm'."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    @pytest.mark.asyncio
    async def test_hybrid_detector_fallback_mode(self):
        """All LLM failure -> mode='rules_only'."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    @pytest.mark.asyncio
    async def test_hybrid_detector_hybrid_mode(self):
        """Partial LLM success -> mode='hybrid'."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    @pytest.mark.asyncio
    async def test_hybrid_detector_language_detection(self):
        """Auto language detection for Hebrew vs English."""
        pass


class TestAnalysisModeResponse:
    """Tests for analysis_mode in API response."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    @pytest.mark.asyncio
    async def test_analysis_response_includes_mode(self, test_client):
        """AnalysisResponse includes analysis_mode field."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-03")
    @pytest.mark.asyncio
    async def test_analysis_mode_reflects_actual_method(self, test_client):
        """analysis_mode accurately reflects detection method used."""
        pass
