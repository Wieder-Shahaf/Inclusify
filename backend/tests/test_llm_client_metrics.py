"""
Unit tests for metric collection in VLLMClient.analyze_sentence().

Verifies that CallMetrics is populated correctly for every outcome:
success, timeout, circuit breaker, HTTP error, and unexpected exception.
No real vLLM endpoint is needed — all HTTP calls are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.modules.analysis.call_metrics import CallMetrics


def _make_mock_http_client(response=None, side_effect=None):
    """Helper to build a mock httpx.AsyncClient context manager."""
    mock_instance = AsyncMock()
    if side_effect:
        mock_instance.post.side_effect = side_effect
    else:
        mock_instance.post.return_value = response

    mock_class = MagicMock()
    mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_class


def _get_vllm():
    from app.modules.analysis.llm_client import VLLMClient
    return VLLMClient


def _get_cbe():
    from pybreaker import CircuitBreakerError
    return CircuitBreakerError


def _success_response(content='{"category": "N/A", "severity": "Correct", "explanation": "OK"}'):
    resp = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": content}, "logprobs": None}]
    }
    resp.raise_for_status = MagicMock()
    resp.status_code = 200
    return resp


class TestAnalyzeSentenceWithoutMetrics:
    """Passing metrics=None must behave identically to old signature."""

    @pytest.mark.asyncio
    async def test_returns_result_no_metrics(self):
        from app.modules.analysis.llm_client import VLLMClient
        mock_http = _make_mock_http_client(response=_success_response())
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            result = await VLLMClient().analyze_sentence("Test.")
        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout_no_metrics(self):
        from app.modules.analysis.llm_client import VLLMClient
        mock_http = _make_mock_http_client(side_effect=httpx.TimeoutException("t/o"))
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            result = await VLLMClient().analyze_sentence("Test.")
        assert result is None


class TestAnalyzeSentenceMetricsSuccess:
    @pytest.mark.asyncio
    async def test_success_records_one_success(self):
        from app.modules.analysis.llm_client import VLLMClient
        mock_http = _make_mock_http_client(response=_success_response())
        metrics = CallMetrics()
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            await VLLMClient().analyze_sentence("Test.", metrics=metrics)
        assert metrics.llm_calls == 1
        assert metrics.llm_successes == 1
        assert metrics.llm_errors == 0

    @pytest.mark.asyncio
    async def test_success_records_positive_latency(self):
        from app.modules.analysis.llm_client import VLLMClient
        mock_http = _make_mock_http_client(response=_success_response())
        metrics = CallMetrics()
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            await VLLMClient().analyze_sentence("Test.", metrics=metrics)
        assert metrics.avg_latency_ms() is not None
        assert metrics.avg_latency_ms() >= 0.0

    @pytest.mark.asyncio
    async def test_parse_failure_records_error(self):
        from app.modules.analysis.llm_client import VLLMClient
        bad_resp = MagicMock()
        bad_resp.json.return_value = {"choices": [{"message": {"content": "not json"}, "logprobs": None}]}
        bad_resp.raise_for_status = MagicMock()
        bad_resp.status_code = 200
        mock_http = _make_mock_http_client(response=bad_resp)
        metrics = CallMetrics()
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            result = await VLLMClient().analyze_sentence("Test.", metrics=metrics)
        assert result is None
        assert metrics.llm_calls == 1
        assert metrics.llm_successes == 0
        assert metrics.llm_errors == 1


class TestAnalyzeSentenceMetricsErrors:
    @pytest.mark.asyncio
    async def test_timeout_records_timeout_error(self):
        from app.modules.analysis.llm_client import VLLMClient
        mock_http = _make_mock_http_client(side_effect=httpx.TimeoutException("timed out"))
        metrics = CallMetrics()
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            result = await VLLMClient().analyze_sentence("Test.", metrics=metrics)
        assert result is None
        assert metrics.llm_calls == 1
        assert metrics.llm_errors == 1
        assert metrics.llm_timeouts == 1
        assert metrics.circuit_breaker_trips == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_trip(self):
        from app.modules.analysis.llm_client import VLLMClient
        from pybreaker import CircuitBreakerError
        metrics = CallMetrics()
        with patch(
            "app.modules.analysis.llm_client.VLLMClient._make_request",
            side_effect=CircuitBreakerError(),
        ):
            result = await VLLMClient().analyze_sentence("Test.", metrics=metrics)
        assert result is None
        assert metrics.llm_calls == 1
        assert metrics.llm_errors == 1
        assert metrics.circuit_breaker_trips == 1
        assert metrics.llm_timeouts == 0

    @pytest.mark.asyncio
    async def test_http_status_error_records_error(self):
        from app.modules.analysis.llm_client import VLLMClient
        http_err_resp = MagicMock()
        http_err_resp.status_code = 500
        http_err = httpx.HTTPStatusError("500", request=MagicMock(), response=http_err_resp)
        mock_http = _make_mock_http_client(side_effect=http_err)
        metrics = CallMetrics()
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            result = await VLLMClient().analyze_sentence("Test.", metrics=metrics)
        assert result is None
        assert metrics.llm_calls == 1
        assert metrics.llm_errors == 1
        assert metrics.llm_timeouts == 0

    @pytest.mark.asyncio
    async def test_unexpected_exception_records_generic_error(self):
        from app.modules.analysis.llm_client import VLLMClient
        mock_http = _make_mock_http_client(side_effect=RuntimeError("boom"))
        metrics = CallMetrics()
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", mock_http):
            result = await VLLMClient().analyze_sentence("Test.", metrics=metrics)
        assert result is None
        assert metrics.llm_calls == 1
        assert metrics.llm_errors == 1

    @pytest.mark.asyncio
    async def test_multiple_calls_accumulate(self):
        from app.modules.analysis.llm_client import VLLMClient
        from pybreaker import CircuitBreakerError as CBE
        idx = 0
        responses = [True, "timeout", "cbe"]

        async def mock_make_request(sentence):
            nonlocal idx
            val = responses[idx]
            idx += 1
            if val == "timeout":
                raise httpx.TimeoutException("t/o")
            if val == "cbe":
                raise CBE()
            return {"category": "N/A", "severity": "Correct", "explanation": "OK", "confidence": None}

        metrics = CallMetrics()
        client = VLLMClient()
        with patch.object(client, "_make_request", side_effect=mock_make_request):
            await client.analyze_sentence("s1", metrics=metrics)
            await client.analyze_sentence("s2", metrics=metrics)
            await client.analyze_sentence("s3", metrics=metrics)

        assert metrics.llm_calls == 3
        assert metrics.llm_successes == 1
        assert metrics.llm_errors == 2
        assert metrics.llm_timeouts == 1
        assert metrics.circuit_breaker_trips == 1
