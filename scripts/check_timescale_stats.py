
import asyncio
import asyncpg
import os
from datetime import datetime

# DB Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

async def check_timescale():
    try:
        print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}...")
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        print("✅ Connected to TimescaleDB")

        # Check counts by day for the requested period
        query = """
        SELECT time_bucket('1 day', time) as day, count(*) as cnt
        FROM market_ticks
        WHERE time >= '2026-01-14'
        GROUP BY day
        ORDER BY day;
        """
        
        print("\n[Daily Tick Counts]")
        rows = await conn.fetch(query)
        for row in rows:
            print(f"{row['day'].date()}: {row['cnt']:,}")

        # Check schema just in case
        print("\n[Schema Info]")
        types = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'market_ticks'")
        for t in types:
            print(f"- {t['column_name']}: {t['data_type']}")
            
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_timescale())
