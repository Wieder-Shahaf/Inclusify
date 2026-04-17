import asyncio
import os
import asyncpg
from dotenv import load_dotenv, find_dotenv
from app.modules.admin.queries import get_analytics_kpis

# Automatically find .env regardless of whether it's in the backend or root folder
load_dotenv(find_dotenv())

async def test_admin_queries():
    # Load database variables from .env
    pg_user = os.getenv("PGUSER", "postgres")
    pg_pass = os.getenv("PGPASSWORD", "devpassword")
    pg_host = os.getenv("PGHOST", "localhost")
    pg_port = os.getenv("PGPORT", "5432")
    pg_db   = os.getenv("PGDATABASE", "inclusify")
    
    # Constructing URL
    db_url = os.getenv("DATABASE_URL", f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}")
    
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
        print("Connected! Running get_analytics_kpis for the last 30 days...\n")
        
        # Run the updated query
        kpis = await get_analytics_kpis(conn, days=30)
        
        print("=== Analytics KPIs ===")
        for key, value in kpis.items():
            print(f"{key}: {value}")
            
        print("\n[SUCCESS] Test passed! Timezone query executed successfully.")
        
    except Exception as e:
        print(f"\n[ERROR] Error occurred: {e}")
    finally:
        if 'conn' in locals() and not conn.is_closed():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(test_admin_queries())
