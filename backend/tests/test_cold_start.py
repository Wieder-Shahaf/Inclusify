"""A dud analysis must never be reported as a perfect score.

Regression cover for the Modal cold-start bug: the GPU scales to zero, the next
cold start measured 183s (2026-07-29) — longer than the detector's 180s fan-out
cap — so every chunk task was cancelled, the empty issue list scored 100% clean,
and the user got a flawless report on an un-analysed paper.

Three guards, one per link in that chain:
  1. /analyze waits for the model before spending the analysis budget
  2. the fan-out cap keeps chunks that finished instead of dropping all of them
  3. a run where every chunk failed returns 503, never a score
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _models_response(ids):
    resp = MagicMock()
    resp.json.return_value = {"data": [{"id": i} for i in ids]}
    resp.raise_for_status = MagicMock()
    return resp


def _mock_http(response=None, side_effect=None):
    """Mock httpx.AsyncClient whose .get() returns `response` / raises `side_effect`."""
    instance = AsyncMock()
    if side_effect is not None:
        instance.get.side_effect = side_effect
    else:
        instance.get.return_value = response
    cls = MagicMock()
    cls.return_value.__aenter__ = AsyncMock(return_value=instance)
    cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return cls


class TestWaitUntilModelReady:
    """The readiness gate polls /v1/models — cheap, and only 200s once the LoRA
    adapter is registered (vLLM serves no HTTP before that)."""

    @pytest.mark.asyncio
    async def test_ready_when_adapter_is_served(self):
        from app.modules.analysis.llm_client import wait_until_model_ready

        http = _mock_http(_models_response(["Qwen/Qwen2.5-3B-Instruct", "inclusify"]))
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", http):
            assert await wait_until_model_ready(budget_s=5.0) is True

    @pytest.mark.asyncio
    async def test_gives_up_when_endpoint_never_answers(self):
        """Cold start longer than the budget → False, so the caller can 503 rather
        than run an analysis that is guaranteed to produce nothing."""
        import httpx
        from app.modules.analysis.llm_client import wait_until_model_ready

        http = _mock_http(side_effect=httpx.ConnectError("connection refused"))
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", http):
            assert await wait_until_model_ready(budget_s=0.2) is False

    @pytest.mark.asyncio
    async def test_proceeds_when_server_up_but_adapter_missing(self):
        """A missing adapter is a deploy fault, not a cold start — polling can't fix
        it, so don't hang for the whole budget."""
        from app.modules.analysis.llm_client import wait_until_model_ready

        http = _mock_http(_models_response(["Qwen/Qwen2.5-3B-Instruct"]))
        with patch("app.modules.analysis.llm_client.httpx.AsyncClient", http):
            assert await wait_until_model_ready(budget_s=30.0) is True


class TestFanOutTimeoutKeepsCompletedChunks:
    @pytest.mark.asyncio
    async def test_slow_chunk_does_not_discard_finished_ones(self, monkeypatch):
        from app.modules.analysis import hybrid_detector as hd

        monkeypatch.setattr(hd, "OVERALL_ANALYSIS_TIMEOUT_S", 0.3)

        async def analyze(sentence, metrics=None):
            # The chunk holding the offending phrase answers; the other hangs past
            # the cap, which used to take the whole run down with it.
            if "homosexual" in sentence:
                if metrics is not None:
                    metrics.record_call(10.0, success=True)
                return {"issues": [{
                    "phrase": "homosexual lifestyle",
                    "category": "Demeaning Terminology",
                    "severity": "Outdated",
                    "explanation": "Outdated framing.",
                    "suggestion": "sexual orientation",
                    "confidence": 0.9,
                }]}
            await asyncio.sleep(30)
            return None

        client = MagicMock()
        client.analyze_sentence = analyze
        client.get_suggestion = AsyncMock(return_value="sexual orientation")

        issues, _, metrics = await hd.HybridDetector(vllm_client=client).analyze(
            "The homosexual lifestyle is outdated terminology. This chunk hangs forever."
        )

        assert len(issues) == 1, "completed chunk was thrown away with the slow one"
        assert issues[0].phrase == "homosexual lifestyle"
        assert metrics.llm_successes == 1


class TestTotalFailureIsNotAScore:
    @pytest.mark.asyncio
    async def test_all_chunks_failed_returns_503(self, test_client, monkeypatch):
        """Every chunk failing used to return 200 with score=100."""
        from app.modules.analysis.router import _hybrid_detector

        client = MagicMock()
        client.analyze_sentence = AsyncMock(return_value=None)
        monkeypatch.setattr(_hybrid_detector, "client", client)

        resp = await test_client.post(
            "/api/v1/analysis/analyze",
            json={"text": "The homosexual lifestyle is outdated terminology.",
                  "private_mode": True},
        )

        assert resp.status_code == 503
        assert "score" not in resp.json()

    @pytest.mark.asyncio
    async def test_model_never_warms_returns_503(self, test_client, monkeypatch):
        monkeypatch.setattr(
            "app.modules.analysis.router.wait_until_model_ready",
            AsyncMock(return_value=False),
        )

        resp = await test_client.post(
            "/api/v1/analysis/analyze",
            json={"text": "The homosexual lifestyle is outdated terminology.",
                  "private_mode": True},
        )

        assert resp.status_code == 503
        assert "starting up" in resp.json()["detail"]
