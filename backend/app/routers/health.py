"""Health check endpoint with deep DB validation.

Provides:
- Overall health status
- Database connectivity check with latency
- Pool statistics (size, free, used, limits)
- Version information (commit, build time)

Returns 200 if healthy, 503 if DB unreachable.
"""
import os
import asyncio
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

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
