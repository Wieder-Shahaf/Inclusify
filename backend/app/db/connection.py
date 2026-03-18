import logging
import os
from typing import Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


async def create_pool() -> Optional[asyncpg.Pool]:
    """Create asyncpg connection pool with configured limits.

    Returns None if PostgreSQL env vars are not set (local dev without PG).

    Pool configuration:
    - min=2, max=10 (conservative for Azure B1ms 50-connection limit)
    - command_timeout=60 (query timeout)
    - max_inactive_connection_lifetime=300 (5 min idle cleanup)
    - SSL conditional on PGSSL env var
    """
    pg_host = os.environ.get("PGHOST")
    if not pg_host:
        logger.warning("PGHOST not set — skipping asyncpg pool creation")
        return None

    ssl_mode = os.environ.get("PGSSL")

    return await asyncpg.create_pool(
        host=pg_host,
        port=int(os.environ.get("PGPORT", 5432)),
        database=os.environ.get("PGDATABASE", "inclusify"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
        min_size=2,
        max_size=10,
        command_timeout=60,
        max_inactive_connection_lifetime=300.0,
        ssl="require" if ssl_mode else None,
    )


# Keep legacy function for compatibility (deprecated)
async def get_conn() -> asyncpg.Connection:
    """DEPRECATED: Use pool via get_db dependency instead."""
    return await asyncpg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        ssl="require" if os.environ.get("PGSSL") else None,
    )
