import asyncio
import asyncpg
from datetime import datetime

async def check_today_kr_data():
    try:
        conn = await asyncpg.connect(
            user="postgres", 
            password="password", 
            database="stockval", 
            host="localhost"
        )
        
        # Check for today's data in market_ticks (KR stocks)
        # KR stocks: 005930, 000660, 035420, etc.
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_ticks,
                MIN(time) as first_tick,
                MAX(time) as last_tick,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM market_ticks
            WHERE time >= '2026-01-09 00:00:00+09'
              AND time < '2026-01-10 00:00:00+09'
        """)
        
        print(f"=== Today's Market Data (2026-01-09) ===")
        print(f"Total ticks: {result['total_ticks']}")
        print(f"Unique symbols: {result['unique_symbols']}")
        print(f"First tick: {result['first_tick']}")
        print(f"Last tick: {result['last_tick']}")
        
        # Get sample data
        if result['total_ticks'] > 0:
            samples = await conn.fetch("""
                SELECT time, symbol, price, volume
                FROM market_ticks
                WHERE time >= '2026-01-09 00:00:00+09'
                  AND time < '2026-01-10 00:00:00+09'
                ORDER BY time DESC
                LIMIT 10
            """)
            print(f"\nRecent 10 ticks:")
            for s in samples:
                print(f"  {s['time']} | {s['symbol']} | {s['price']} | vol:{s['volume']}")
                
            # Check market hours data (09:00-15:30)
            market_hours = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM market_ticks
                WHERE time >= '2026-01-09 09:00:00+09'
                  AND time <= '2026-01-09 15:30:00+09'
            """)
            print(f"\nMarket hours (09:00-15:30) ticks: {market_hours['count']}")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(check_today_kr_data())
