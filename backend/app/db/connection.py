import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        ssl="require",
    )
