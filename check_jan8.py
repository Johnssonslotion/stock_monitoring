import asyncio
import asyncpg

async def check_jan8_data():
    try:
        conn = await asyncpg.connect(
            user="postgres", 
            password="password", 
            database="stockval", 
            host="localhost"
        )
        
        # Jan 8 market hours data
        jan8 = await conn.fetchrow("""
            SELECT 
                COUNT(*) as count,
                MIN(time) as first,
                MAX(time) as last
            FROM market_ticks
            WHERE time >= '2026-01-08 09:00:00+09'
              AND time <= '2026-01-08 15:30:00+09'
        """)
        
        print(f"=== Jan 8 Market Hours (09:00-15:30 KST) ===")
        print(f"Count: {jan8['count']}")
        print(f"First: {jan8['first']}")
        print(f"Last: {jan8['last']}")
        
        # Jan 5-7 data
        prev_days = await conn.fetch("""
            SELECT DATE(time AT TIME ZONE 'Asia/Seoul') as date, COUNT(*) as count
            FROM market_ticks
            WHERE time >= '2026-01-05'
            GROUP BY DATE(time AT TIME ZONE 'Asia/Seoul')
            ORDER BY date
        """)
        print(f"\nDaily breakdown:")
        for d in prev_days:
            print(f"  {d['date']}: {d['count']:,} ticks")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(check_jan8_data())
