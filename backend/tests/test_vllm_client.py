"""
Tests for vLLM client, circuit breaker, and sentence splitter modules.

Tests organized by module:
- TestVLLMSettings: Configuration tests
- TestCircuitBreaker: Circuit breaker behavior
- TestSentenceSplitter: Sentence splitting with offsets
- TestParseOutput: LLM output parsing
- TestSeverityMapping: Severity mapping
- TestVLLMClient: Client integration
"""

import pytest


class TestVLLMSettings:
    """Test vLLM settings in config."""

    def test_settings_has_vllm_url(self):
        """Settings should have VLLM_URL field."""
        from app.core.config import settings
        assert hasattr(settings, 'VLLM_URL')
        assert settings.VLLM_URL == "http://localhost:8001"

    def test_settings_has_vllm_timeout(self):
        """Settings should have VLLM_TIMEOUT field."""
        from app.core.config import settings
        assert hasattr(settings, 'VLLM_TIMEOUT')
        assert settings.VLLM_TIMEOUT == 120.0

    def test_settings_has_circuit_fail_max(self):
        """Settings should have VLLM_CIRCUIT_FAIL_MAX field."""
        from app.core.config import settings
        assert hasattr(settings, 'VLLM_CIRCUIT_FAIL_MAX')
        assert settings.VLLM_CIRCUIT_FAIL_MAX == 3

    def test_settings_has_circuit_reset_timeout(self):
        """Settings should have VLLM_CIRCUIT_RESET_TIMEOUT field."""
        from app.core.config import settings
        assert hasattr(settings, 'VLLM_CIRCUIT_RESET_TIMEOUT')
        assert settings.VLLM_CIRCUIT_RESET_TIMEOUT == 60


class TestCircuitBreaker:
    """Test circuit breaker behavior."""

    @pytest.fixture
    def fresh_breaker(self):
        """Create a fresh circuit breaker for each test to avoid state leakage."""
        from pybreaker import CircuitBreaker
        return CircuitBreaker(
            fail_max=3,
            reset_timeout=1  # 1 second for fast tests
        )

    def test_circuit_breaker_opens_after_failures(self, fresh_breaker):
        """Circuit opens after fail_max consecutive failures."""
        from pybreaker import CircuitBreakerError

        @fresh_breaker
        def failing_func():
            raise Exception("Simulated failure")

        # Fail 3 times to open the circuit
        for _ in range(3):
            try:
                failing_func()
            except Exception:
                pass

        # Now circuit should be open - should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            failing_func()

    def test_circuit_breaker_auto_recovers(self, fresh_breaker):
        """Circuit auto-recovers after reset_timeout."""
        import time
        from pybreaker import CircuitBreakerError

        call_count = 0

        @fresh_breaker
        def recoverable_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Simulated failure")
            return "success"

        # Fail 3 times to open the circuit
        for _ in range(3):
            try:
                recoverable_func()
            except Exception:
                pass

        # Circuit should be open
        with pytest.raises(CircuitBreakerError):
            recoverable_func()

        # Wait for reset_timeout (1 second)
        time.sleep(1.1)

        # Circuit should be half-open, next call should succeed
        result = recoverable_func()
        assert result == "success"

    def test_circuit_breaker_module_exports(self):
        """Circuit breaker module exports vllm_breaker and CircuitBreakerError."""
        from app.modules.analysis.circuit_breaker import vllm_breaker, CircuitBreakerError
        assert vllm_breaker is not None
        assert CircuitBreakerError is not None


class TestSentenceSplitter:
    """Test sentence splitting with offsets."""

    def test_sentence_split_english(self):
        """English text splits with correct offsets."""
        from app.modules.analysis.sentence_splitter import split_with_offsets

        result = split_with_offsets("Hello. World.", "en")

        # Should return list of (sentence, start, end) tuples
        assert len(result) == 2
        assert result[0][0] == "Hello."
        assert result[0][1] == 0  # start offset
        assert result[0][2] == 6  # end offset
        assert result[1][0] == "World."
        assert result[1][1] == 7  # start offset
        assert result[1][2] == 13  # end offset

    def test_sentence_split_hebrew(self):
        """Hebrew text splits without breaking mid-word."""
        from app.modules.analysis.sentence_splitter import split_with_offsets

        # Simple Hebrew sentences with period
        hebrew_text = "שלום עולם. מה שלומך?"
        result = split_with_offsets(hebrew_text, "he")

        # Should have 2 sentences
        assert len(result) == 2
        # First sentence should not be broken mid-word
        assert "שלום עולם." in result[0][0]

    def test_sentence_split_empty(self):
        """Empty string returns empty list."""
        from app.modules.analysis.sentence_splitter import split_with_offsets

        result = split_with_offsets("", "en")
        assert result == []

    def test_sentence_split_single(self):
        """Single sentence returns list with one tuple."""
        from app.modules.analysis.sentence_splitter import split_with_offsets

        result = split_with_offsets("Just one sentence.", "en")
        assert len(result) == 1
        assert result[0][0] == "Just one sentence."
        assert result[0][1] == 0
        assert result[0][2] == 18


class TestParseOutput:
    """Test LLM output parsing."""

    def test_parse_llm_output_valid(self):
        """Valid JSON parses correctly."""
        from app.modules.analysis.llm_client import parse_llm_output

        raw = '{"category": "N/A", "severity": "Correct", "explanation": "Good text"}'
        result = parse_llm_output(raw)

        assert result is not None
        assert result["category"] == "N/A"
        assert result["severity"] == "Correct"
        assert result["explanation"] == "Good text"

    def test_parse_llm_output_markdown(self):
        """JSON in markdown code block parses correctly."""
        from app.modules.analysis.llm_client import parse_llm_output

        raw = '''```json
{"category": "Historical Pathologization", "severity": "Outdated", "explanation": "Uses outdated terminology"}
```'''
        result = parse_llm_output(raw)

        assert result is not None
        assert result["category"] == "Historical Pathologization"
        assert result["severity"] == "Outdated"

    def test_parse_llm_output_invalid(self):
        """Invalid JSON returns None."""
        from app.modules.analysis.llm_client import parse_llm_output

        result = parse_llm_output("This is not JSON at all")
        assert result is None

        result = parse_llm_output("{invalid json}")
        assert result is None


class TestSeverityMapping:
    """Test severity mapping."""

    def test_map_severity_all_cases(self):
        """Severity mapping works correctly."""
        from app.modules.analysis.llm_client import map_severity

        assert map_severity("Outdated") == "outdated"
        assert map_severity("Biased") == "biased"
        assert map_severity("Potentially Offensive") == "potentially_offensive"
        assert map_severity("Factually Incorrect") == "factually_incorrect"

    def test_map_severity_correct_returns_none(self):
        """'Correct' severity returns None to skip."""
        from app.modules.analysis.llm_client import map_severity

        result = map_severity("Correct")
        assert result is None


class TestVLLMClient:
    """Test vLLM client."""

    @pytest.fixture
    def mock_vllm_response(self):
        """Create mock httpx response with valid JSON."""
        from unittest.mock import MagicMock

        response = MagicMock()
        response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"category": "N/A", "severity": "Correct", "explanation": "Good"}'
                }
            }]
        }
        response.raise_for_status = MagicMock()
        return response

    @pytest.mark.asyncio
    async def test_vllm_client_success(self, mock_vllm_response):
        """Client returns parsed response on success."""
        from unittest.mock import AsyncMock, patch, MagicMock
        from app.modules.analysis.llm_client import VLLMClient

        # Create async context manager mock
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_vllm_response

        mock_client_class = MagicMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('app.modules.analysis.llm_client.httpx.AsyncClient', mock_client_class):
            client = VLLMClient()
            result = await client.analyze_sentence("Test sentence.")

        assert result is not None
        assert result["category"] == "N/A"
        assert result["severity"] == "Correct"

    @pytest.mark.asyncio
    async def test_vllm_client_timeout(self):
        """Client returns None on timeout."""
        from unittest.mock import AsyncMock, patch, MagicMock
        import httpx
        from app.modules.analysis.llm_client import VLLMClient

        # Create async context manager mock that raises timeout
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Timeout")

        mock_client_class = MagicMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('app.modules.analysis.llm_client.httpx.AsyncClient', mock_client_class):
            client = VLLMClient()
            result = await client.analyze_sentence("Test sentence.")

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_body,label", [
        ({}, "missing choices key"),
        ({"choices": []}, "empty choices list"),
        ({"choices": ["not-a-dict"]}, "choice not a dict"),
        ({"choices": [{"no_message": True}]}, "missing message key"),
        ({"choices": [{"message": {"no_content": True}}]}, "missing content key"),
    ])
    async def test_vllm_client_malformed_response_returns_none(self, bad_body, label):
        """Client returns None on any malformed vLLM response shape without raising."""
        from unittest.mock import AsyncMock, patch, MagicMock
        from app.modules.analysis.llm_client import VLLMClient

        mock_response = MagicMock()
        mock_response.json.return_value = bad_body
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response

        mock_client_class = MagicMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('app.modules.analysis.llm_client.httpx.AsyncClient', mock_client_class):
            client = VLLMClient()
            result = await client.analyze_sentence("Test sentence.")

        assert result is None, f"Expected None for: {label}"

    @pytest.mark.asyncio
    async def test_vllm_client_circuit_open(self):
        """Client returns None when circuit is open."""
        from unittest.mock import AsyncMock, patch, MagicMock
        from pybreaker import CircuitBreakerError
        from app.modules.analysis.llm_client import VLLMClient

        # Create async context manager mock that raises CircuitBreakerError
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = CircuitBreakerError()

        mock_client_class = MagicMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('app.modules.analysis.llm_client.httpx.AsyncClient', mock_client_class):
            client = VLLMClient()
            result = await client.analyze_sentence("Test sentence.")

        assert result is None
