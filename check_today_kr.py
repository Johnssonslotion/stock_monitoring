import asyncio
import asyncpg

async def check_today_data():
    try:
        conn = await asyncpg.connect(
            user="postgres", 
            password="password", 
            database="stockval", 
            host="localhost"
        )
        
        # Check if table exists
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        print(f"Available tables: {[t['tablename'] for t in tables]}")
        
        # Check for today's KR stock data (if ticks table exists)
        try:
            today_count = await conn.fetchrow("""
                SELECT COUNT(*) as count, MIN(timestamp) as first, MAX(timestamp) as last
                FROM ticks 
                WHERE timestamp >= '2026-01-09 00:00:00+09'
                  AND timestamp < '2026-01-10 00:00:00+09'
                  AND symbol LIKE '%KR%' OR symbol IN ('005930', '000660', '035420')
            """)
            print(f"\nToday's KR stock ticks: {today_count}")
        except Exception as e:
            print(f"No ticks table or error: {e}")
        
        await conn.close()
    except Exception as e:
        print(f"DB connection error: {e}")

asyncio.run(check_today_data())
