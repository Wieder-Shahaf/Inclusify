import pytest

import app.routers.health as health_mod
from app.core.config import settings as app_settings


# --- /api/v1/health/model — Stack A §2.3 (scale-to-zero + probe cache) --------

class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _CountingClient:
    """httpx.AsyncClient stand-in that counts probe calls."""
    calls = 0

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        type(self).calls += 1
        return _FakeResp({"data": [{"id": "inclusify"}]})


class _ExplodingClient:
    """Fails the test if the GPU is probed when it must not be."""
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        raise AssertionError("vLLM must not be probed in this mode")


class _Breaker:
    def __init__(self, state):
        self.current_state = state


def _reset_model_health_cache():
    health_mod._model_health_cache = None
    health_mod._model_health_cache_ts = 0.0


@pytest.mark.asyncio
async def test_model_health_scale_to_zero_reports_available_without_probing(test_client, monkeypatch):
    """Serverless mode: report available + state=scale_to_zero, never touch vLLM."""
    _reset_model_health_cache()
    monkeypatch.setattr(app_settings, "MODEL_SCALE_TO_ZERO", True)
    monkeypatch.setattr("app.modules.analysis.circuit_breaker.vllm_breaker", _Breaker("closed"))
    monkeypatch.setattr(health_mod.httpx, "AsyncClient", _ExplodingClient)

    resp = await test_client.get("/api/v1/health/model")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "available"
    assert data["state"] == "scale_to_zero"
    assert data["response_time_ms"] is None


@pytest.mark.asyncio
async def test_model_health_circuit_open_returns_503_without_probing(test_client, monkeypatch):
    """Open breaker => unavailable, no network call (either mode)."""
    _reset_model_health_cache()
    monkeypatch.setattr(app_settings, "MODEL_SCALE_TO_ZERO", False)
    monkeypatch.setattr("app.modules.analysis.circuit_breaker.vllm_breaker", _Breaker("open"))
    monkeypatch.setattr(health_mod.httpx, "AsyncClient", _ExplodingClient)

    resp = await test_client.get("/api/v1/health/model")
    assert resp.status_code == 503
    assert resp.json()["status"] == "unavailable"


@pytest.mark.asyncio
async def test_model_health_probe_is_cached(test_client, monkeypatch):
    """Always-on mode: the live probe is cached, so a second poll within TTL
    does not hit vLLM again."""
    _reset_model_health_cache()
    _CountingClient.calls = 0
    monkeypatch.setattr(app_settings, "MODEL_SCALE_TO_ZERO", False)
    monkeypatch.setattr(app_settings, "MODEL_HEALTH_CACHE_TTL", 300.0)
    monkeypatch.setattr("app.modules.analysis.circuit_breaker.vllm_breaker", _Breaker("closed"))
    monkeypatch.setattr(health_mod.httpx, "AsyncClient", _CountingClient)

    r1 = await test_client.get("/api/v1/health/model")
    r2 = await test_client.get("/api/v1/health/model")

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()
    assert _CountingClient.calls == 1  # second response served from cache


# --- /health (DB) -------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_returns_200_with_db_connected(test_client):
    """Health endpoint returns 200 when DB is reachable"""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_includes_pool_stats(test_client):
    """Health response includes pool statistics"""
    response = await test_client.get("/health")
    data = response.json()
    assert "pool" in data
    assert "size" in data["pool"]
    assert "free" in data["pool"]
    assert "min" in data["pool"]
    assert "max" in data["pool"]


@pytest.mark.asyncio
async def test_health_includes_version(test_client):
    """Health response includes version information"""
    response = await test_client.get("/health")
    data = response.json()
    assert "version" in data
    assert "commit" in data["version"]
    assert "build_time" in data["version"]


@pytest.mark.asyncio
async def test_health_db_latency_present(test_client):
    """Health response includes DB latency measurement"""
    response = await test_client.get("/health")
    data = response.json()
    assert "components" in data
    assert "database" in data["components"]
    assert "latency_ms" in data["components"]["database"]
