"""
Test stubs for vLLM client, circuit breaker, and sentence splitter.
These tests will fail until Plan 03-02 implementation completes.
"""
import pytest


class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_circuit_breaker_opens_after_failures(self):
        """Circuit breaker opens after 3 consecutive failures."""
        # After 3 failures, CircuitBreakerError raised on next call
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_circuit_breaker_auto_recovers(self):
        """Circuit breaker auto-recovers after timeout."""
        # After reset_timeout (60s), circuit moves to half-open
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_circuit_breaker_closes_on_success(self):
        """Successful call in half-open state closes circuit."""
        pass


class TestSentenceSplitter:
    """Tests for sentence splitting with offsets."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_sentence_split_english(self, sample_text_english):
        """English text splits with correct offsets."""
        # "Hello. World." -> [("Hello.", 0, 6), ("World.", 7, 13)]
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_sentence_split_hebrew(self, sample_text_hebrew):
        """Hebrew text splits correctly without breaking mid-word."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_sentence_split_empty(self):
        """Empty string returns empty list."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_sentence_split_single(self):
        """Single sentence returns list with one tuple."""
        pass


class TestVLLMClient:
    """Tests for async vLLM HTTP client."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    @pytest.mark.asyncio
    async def test_analyze_sentence_success(self, mock_vllm_response):
        """Successful analysis returns parsed JSON."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    @pytest.mark.asyncio
    async def test_analyze_sentence_timeout(self, mock_vllm_timeout_response):
        """Timeout returns None instead of raising."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    @pytest.mark.asyncio
    async def test_analyze_sentence_circuit_open(self):
        """Returns None when circuit breaker is open."""
        pass


class TestParseOutput:
    """Tests for LLM output parsing."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_parse_llm_output_valid(self):
        """Valid JSON parsing."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_parse_llm_output_markdown(self):
        """JSON in markdown code block."""
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_parse_llm_output_invalid(self):
        """Returns None for invalid JSON."""
        pass


class TestSeverityMapping:
    """Tests for severity mapping."""

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_map_severity_all_cases(self):
        """All severity mappings correct."""
        # Outdated -> outdated, Biased -> biased, etc.
        pass

    @pytest.mark.skip(reason="Wave 0 stub - implement in 03-02")
    def test_map_severity_correct_returns_none(self):
        """'Correct' severity returns None (skip)."""
        pass
