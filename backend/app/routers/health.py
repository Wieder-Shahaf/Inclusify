"""Health check endpoints.

Provides:
- GET /health — deep DB check with pool stats and version info
- GET /api/v1/health/model — vLLM availability, latency, circuit breaker state

Returns 200 if healthy, 503 if component unreachable.
"""
import os
import asyncio
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx

router = APIRouter(tags=["Health"])


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

    Response format:
    {
        "status": "available" | "unavailable",
        "model": "<model name>",
        "response_time_ms": <float> | null,
        "circuit_breaker": "closed" | "open" | "half_open",
        "error": "<reason>"   // only present when unavailable
    }
    """
    from app.modules.analysis.circuit_breaker import vllm_breaker
    from app.core.config import settings

    raw_state = vllm_breaker.current_state
    cb_state: str = raw_state.name if hasattr(raw_state, 'name') else str(raw_state)

    # Skip the network call entirely when the circuit is open
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

    # Ping vLLM /v1/models with a tight timeout
    start = datetime.now()
    available = False
    model_name: str = settings.VLLM_MODEL_NAME
    error: str | None = None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.VLLM_URL}/v1/models")
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

    return JSONResponse(content=body, status_code=200 if available else 503)
