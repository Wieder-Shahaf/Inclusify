from fastapi import Request
from typing import AsyncGenerator
import asyncpg

async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        yield conn
