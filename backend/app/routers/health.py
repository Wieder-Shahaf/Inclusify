"""Health check endpoints.

Provides:
- GET /health — deep DB check with pool stats and version info
- GET /api/v1/health/model — vLLM availability, latency, circuit breaker state

Returns 200 if healthy, 503 if component unreachable.
"""
import os
import asyncio
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx

router = APIRouter(tags=["Health"])

# --- Model health cache (see /api/v1/health/model) ---------------------------
# Guards the live vLLM probe so that, on an always-on backend, a roomful of open
# analyze tabs polling every 30s can't turn into 30s-interval load on vLLM. The
# lock prevents a probe stampede when several polls arrive with a cold cache.
_model_health_cache: Optional[dict] = None
_model_health_cache_ts: float = 0.0
_model_health_lock = asyncio.Lock()


@router.get("/health")
async def health_check(request: Request):
    """Deep health check with DB connectivity and pool stats.

    Response format per CONTEXT.md:
    {
        "status": "healthy" | "unhealthy",
        "components": {
            "database": {"status": "...", "latency_ms": ...}
        },
        "pool": {"size": ..., "free": ..., "used": ..., "min": ..., "max": ...},
        "version": {"commit": "...", "build_time": "..."}
    }
    """
    pool = getattr(request.app.state, "db_pool", None)
    db_status = "unhealthy"
    db_latency_ms = None
    db_error = None
    pool_stats = None

    if pool is None:
        db_error = "database pool not initialized"
    else:
        # Check DB connectivity with 3s timeout
        async def _check_db():
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

        try:
            start = datetime.now()
            await asyncio.wait_for(_check_db(), timeout=3.0)
            db_latency_ms = round((datetime.now() - start).total_seconds() * 1000, 2)
            db_status = "healthy"
        except asyncio.TimeoutError:
            db_error = "timeout"
        except Exception as e:
            db_error = str(e)[:100]  # Truncate long errors

        pool_stats = {
            "size": pool.get_size(),
            "free": pool.get_idle_size(),
            "used": pool.get_size() - pool.get_idle_size(),
            "min": pool.get_min_size(),
            "max": pool.get_max_size(),
        }

    # Determine overall status
    overall = "healthy" if db_status == "healthy" else "unhealthy"
    status_code = 200 if overall == "healthy" else 503

    response_data = {
        "status": overall,
        "components": {
            "database": {
                "status": db_status,
                "latency_ms": db_latency_ms,
                **({"error": db_error} if db_error else {}),
            }
        },
        "pool": pool_stats,
        "version": {
            "commit": os.environ.get("GIT_COMMIT", "unknown"),
            "build_time": os.environ.get("BUILD_TIME", "unknown"),
        }
    }

    return JSONResponse(content=response_data, status_code=status_code)


@router.get("/api/v1/health/model")
async def model_health_check():
    """Check vLLM model availability, latency, and circuit breaker state.

    Two modes:

    - Serverless GPU (settings.MODEL_SCALE_TO_ZERO=True, e.g. Modal): NEVER probe
      vLLM. Any request to a scaled-to-zero endpoint wakes the GPU and bills idle
      time. Availability is inferred from the circuit breaker (which only trips on
      real analysis traffic); when the breaker is not open the model is reported
      available with state="scale_to_zero" so Modal cold-starts on the first real
      analysis request, not on a health poll.

    - Always-on GPU (default, e.g. Azure VM): probe vLLM /v1/models, but cache the
      result for MODEL_HEALTH_CACHE_TTL seconds so many open tabs polling every
      30s don't hammer it.

    Response format (unchanged contract; `state` is additive):
    {
        "status": "available" | "unavailable",
        "model": "<model name>",
        "response_time_ms": <float> | null,
        "circuit_breaker": "closed" | "open" | "half_open",
        "state": "scale_to_zero",   // only in serverless mode
        "error": "<reason>"          // only present when unavailable
    }
    """
    global _model_health_cache, _model_health_cache_ts

    from app.modules.analysis.circuit_breaker import vllm_breaker
    from app.core.config import settings

    raw_state = vllm_breaker.current_state
    cb_state: str = raw_state.name if hasattr(raw_state, 'name') else str(raw_state)

    # Circuit open → recent real failures. Never touch the network (either mode).
    if cb_state == "open":
        return JSONResponse(
            content={
                "status": "unavailable",
                "model": settings.VLLM_MODEL_NAME,
                "response_time_ms": None,
                "circuit_breaker": cb_state,
                "error": "Circuit breaker open — vLLM requests suspended",
            },
            status_code=503,
        )

    # Serverless mode: infer availability from the breaker, never probe vLLM so a
    # health poll can never trigger (or sustain) a GPU cold start.
    if settings.MODEL_SCALE_TO_ZERO:
        return JSONResponse(
            content={
                "status": "available",
                "model": settings.VLLM_MODEL_NAME,
                "response_time_ms": None,
                "circuit_breaker": cb_state,
                "state": "scale_to_zero",
            },
            status_code=200,
        )

    # Always-on mode: serve a cached probe result when it is still fresh.
    now = time.monotonic()
    if _model_health_cache is not None and (now - _model_health_cache_ts) < settings.MODEL_HEALTH_CACHE_TTL:
        return JSONResponse(content=_model_health_cache["body"], status_code=_model_health_cache["status_code"])

    async with _model_health_lock:
        # Re-check after acquiring the lock — another request may have refreshed it.
        now = time.monotonic()
        if _model_health_cache is not None and (now - _model_health_cache_ts) < settings.MODEL_HEALTH_CACHE_TTL:
            return JSONResponse(content=_model_health_cache["body"], status_code=_model_health_cache["status_code"])

        # Ping vLLM /v1/models with a tight timeout
        start = datetime.now()
        available = False
        model_name: str = settings.VLLM_MODEL_NAME
        error: Optional[str] = None

        try:
            auth_headers = (
                {"Authorization": f"Bearer {settings.VLLM_API_KEY}"} if settings.VLLM_API_KEY else {}
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.VLLM_URL}/v1/models", headers=auth_headers)
                resp.raise_for_status()
                models = resp.json().get("data", [])
                if models:
                    model_name = models[0].get("id", settings.VLLM_MODEL_NAME)
                available = True
        except httpx.TimeoutException:
            error = "timeout after 5s"
        except httpx.HTTPStatusError as exc:
            error = f"HTTP {exc.response.status_code}"
        except Exception as exc:
            error = str(exc)[:120]

        response_time_ms = round((datetime.now() - start).total_seconds() * 1000, 2)

        body: dict = {
            "status": "available" if available else "unavailable",
            "model": model_name,
            "response_time_ms": response_time_ms if available else None,
            "circuit_breaker": cb_state,
        }
        if error:
            body["error"] = error
        status_code = 200 if available else 503

        _model_health_cache = {"body": body, "status_code": status_code}
        _model_health_cache_ts = time.monotonic()
        return JSONResponse(content=body, status_code=status_code)
