"""The /analyze endpoint is open to guests and every call occupies a paid GPU,
so the per-caller limit and the input cap are the only things bounding cost.

Covers the three fixes together:
  - a caller is cut off after _RATE_LIMIT analyses in the window
  - text above MAX_ANALYSIS_CHARS is rejected before any GPU work
  - authenticated callers and guests are counted in separate buckets, so one
    abusive guest cannot exhaust a signed-in user's quota
"""

from types import SimpleNamespace

import pytest

from app.modules.analysis import router as analysis_router
from app.modules.analysis.call_metrics import CallMetrics


@pytest.fixture(autouse=True)
def _stub_detector_and_reset_limiter(monkeypatch):
    """Skip real vLLM, and clear the per-process counters between tests."""
    async def fake_analyze(text, language="auto", chunks=None):
        return [], "llm", CallMetrics()

    monkeypatch.setattr(
        "app.modules.analysis.router._hybrid_detector.analyze", fake_analyze
    )
    analysis_router._rate_store.clear()
    yield
    analysis_router._rate_store.clear()


@pytest.mark.asyncio
async def test_caller_is_cut_off_past_the_limit(test_client):
    """The Nth call succeeds; the N+1th is refused without reaching the model."""
    limit = analysis_router._RATE_LIMIT
    body = {"text": "A short sample of academic prose.", "private_mode": True}

    for i in range(limit):
        resp = await test_client.post("/api/v1/analysis/analyze", json=body)
        assert resp.status_code == 200, f"call {i + 1} should have been allowed"

    resp = await test_client.post("/api/v1/analysis/analyze", json=body)
    assert resp.status_code == 429
    assert "Too many analyses" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_text_above_the_cap_is_rejected(test_client):
    """Without this cap a single request could carry unbounded work to the GPU."""
    oversized = "a" * (analysis_router.MAX_ANALYSIS_CHARS + 1)
    resp = await test_client.post(
        "/api/v1/analysis/analyze",
        json={"text": oversized, "private_mode": True},
    )
    assert resp.status_code == 422

    # One character under the cap is still accepted.
    resp = await test_client.post(
        "/api/v1/analysis/analyze",
        json={"text": "a" * analysis_router.MAX_ANALYSIS_CHARS, "private_mode": True},
    )
    assert resp.status_code == 200


def test_guests_and_users_are_counted_separately():
    """Bucketing by the wrong key is what made the existing limiters useless:
    everyone behind one proxy IP shared a counter."""
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.7"))
    user = SimpleNamespace(id="11111111-1111-1111-1111-111111111111")

    guest_key = analysis_router._rate_key(request, None)
    user_key = analysis_router._rate_key(request, user)

    assert guest_key == "ip:203.0.113.7"
    assert user_key == "user:11111111-1111-1111-1111-111111111111"
    assert guest_key != user_key

    # A request with no client info must still yield a usable key, not crash.
    assert analysis_router._rate_key(SimpleNamespace(client=None), None) == "ip:unknown"
