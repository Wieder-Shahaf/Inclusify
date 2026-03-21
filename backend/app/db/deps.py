import asyncio
from typing import AsyncGenerator
from fastapi import Request, HTTPException
import asyncpg


async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency that acquires DB connection from pool.

    Features:
    - Returns 503 if DB pool is not available (PGHOST not set)
    - 5-second timeout on acquire (fail-fast on pool exhaustion)
    - Automatic connection release via context manager

    Usage:
        @app.get("/example")
        async def example(conn: asyncpg.Connection = Depends(get_db)):
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available."
        )

    try:
        async with pool.acquire(timeout=5.0) as conn:
            yield conn
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Database connection pool exhausted. Please try again."
        )
