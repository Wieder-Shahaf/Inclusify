import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def create_pool() -> asyncpg.Pool:
    """Create asyncpg connection pool with configured limits.

    Pool configuration per CONTEXT.md:
    - min=2, max=10 (conservative for Azure B1ms 50-connection limit)
    - command_timeout=60 (query timeout)
    - max_inactive_connection_lifetime=300 (5 min idle cleanup)
    - SSL conditional on PGSSL env var
    """
    ssl_mode = os.environ.get("PGSSL")

    return await asyncpg.create_pool(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", 5432)),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
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
