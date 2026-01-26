import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.db import repository as repo  # noqa: E402

async def get_demo_ids(conn: asyncpg.Connection):
    org = await conn.fetchrow("SELECT org_id FROM organizations ORDER BY created_at DESC LIMIT 1;")
    user = await conn.fetchrow("SELECT user_id FROM users ORDER BY created_at DESC LIMIT 1;")
    return org["org_id"], user["user_id"]

async def main():
    conn = await asyncpg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        ssl="require",
    )
    try:
        org_id, user_id = await get_demo_ids(conn)
        async with conn.transaction():
            doc_id = await repo.create_document(
                conn=conn,
                org_id=org_id,
                user_id=user_id,
                input_type="paste",
                language="he",
                private_mode=True,
            )
            run_id = await repo.create_run(
                conn=conn,
                document_id=doc_id,
                model_version="v0-demo",
                status="running",
                config_snapshot={"mode": "script-demo"},
            )
        print("✅ Inserted document:", doc_id)
        print("✅ Inserted run:", run_id)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
