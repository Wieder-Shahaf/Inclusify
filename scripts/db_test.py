import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def main():
    conn = await asyncpg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        ssl="require",
    )
    rows = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
    )
    print("Tables:", [r["table_name"] for r in rows])
    await conn.close()
    print("✅ Connected OK")

if __name__ == "__main__":
    asyncio.run(main())
