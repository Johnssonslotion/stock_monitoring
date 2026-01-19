
import asyncio
import asyncpg
import os
from datetime import datetime, timedelta

# DB Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

async def validate_today():
    try:
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        print("✅ Connected to TimescaleDB for Daily Validation")

        today = '2026-01-19'
        print(f"\n🔍 Analyzing Data for {today}...")

        # 1. Total Count & Range
        query_stats = """
        SELECT count(*) as total_cnt, min(time) as min_t, max(time) as max_t, count(DISTINCT symbol) as sym_cnt
        FROM market_ticks
        WHERE time >= '2026-01-19 00:00:00' AND time < '2026-01-20 00:00:00';
        """
        stats = await conn.fetchrow(query_stats)
        
        print("\n[Overview]")
        print(f"Total Ticks: {stats['total_cnt']:,}")
        print(f"Time Range: {stats['min_t']} ~ {stats['max_t']}")
        print(f"Unique Symbols: {stats['sym_cnt']}")

        # 2. Hourly Distribution
        print("\n[Hourly Distribution]")
        query_hourly = """
        SELECT extract(hour from time) as h, count(*) as cnt
        FROM market_ticks
        WHERE time >= '2026-01-19 00:00:00' AND time < '2026-01-20 00:00:00'
        GROUP BY h
        ORDER BY h;
        """
        rows = await conn.fetch(query_hourly)
        for row in rows:
            print(f"{int(row['h']):02d}h: {row['cnt']:,}")

        # 3. Gap Analysis (Top 5 Gaps > 10s)
        # Note: Heavy query, limit to a specific symbol for performance if needed
        # Let's pick a top symbol first
        top_symbol_row = await conn.fetchrow("""
            SELECT symbol FROM market_ticks 
            WHERE time >= '2026-01-19' 
            GROUP BY symbol ORDER BY count(*) DESC LIMIT 1
        """)
        
        if top_symbol_row:
            target_sym = top_symbol_row['symbol']
            print(f"\n[Gap Analysis for Top Symbol: {target_sym}]")
            
            query_gaps = """
            SELECT time, next_time, extract(epoch from (next_time - time)) as gap
            FROM (
                SELECT time, lead(time) over (order by time) as next_time
                FROM market_ticks
                WHERE symbol = $1 AND time >= '2026-01-19 00:00:00'
            ) sub
            WHERE (next_time - time) > interval '10 seconds'
            ORDER BY gap DESC
            LIMIT 5;
            """
            gaps = await conn.fetch(query_gaps, target_sym)
            if not gaps:
                print("✅ No significant gaps (>10s) found!")
            else:
                print("⚠️ Found Gaps (>10s):")
                for g in gaps:
                    print(f"- {g['time']} -> {g['next_time']} (Gap: {g['gap']:.1f}s)")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(validate_today())
