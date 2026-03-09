import asyncio
from typing import AsyncGenerator
from fastapi import Request, HTTPException
import asyncpg


async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency that acquires DB connection from pool.

    Features:
    - 5-second timeout on acquire (fail-fast on pool exhaustion)
    - Automatic connection release via context manager
    - Raises 503 if pool is exhausted

    Usage:
        @app.get("/example")
        async def example(conn: asyncpg.Connection = Depends(get_db)):
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = request.app.state.db_pool

    try:
        async with asyncio.timeout(5):  # 5s acquire timeout per CONTEXT.md
            async with pool.acquire() as conn:
                yield conn
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Database connection pool exhausted. Please try again."
        )
