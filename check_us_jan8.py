import asyncio
import asyncpg

async def check_us_data():
    try:
        conn = await asyncpg.connect(
            user="postgres", 
            password="password", 
            database="stockval", 
            host="localhost"
        )
        
        # Check US data for Jan 8
        us_jan8 = await conn.fetchrow("""
            SELECT 
                COUNT(*) as count,
                MIN(time) as first,
                MAX(time) as last
            FROM market_ticks
            WHERE time >= '2026-01-08 00:00:00+00'
              AND time < '2026-01-09 00:00:00+00'
              AND symbol NOT IN ('005930', '000660', '042700', '069500', '122630', '068270', 
                                  '252670', '005380', '102110', '000270', '373220', '233740',
                                  '005490', '012330', '000100', '247540', '207940', '091230',
                                  '305540', '091180')
        """)
        
        print(f"=== US Market Data (Jan 8) ===")
        print(f"Count: {us_jan8['count']}")
        print(f"First: {us_jan8['first']}")
        print(f"Last: {us_jan8['last']}")
        
        # Get US symbols
        if us_jan8['count'] > 0:
            us_symbols = await conn.fetch("""
                SELECT symbol, COUNT(*) as count
                FROM market_ticks
                WHERE time >= '2026-01-08 00:00:00+00'
                  AND time < '2026-01-09 00:00:00+00'
                  AND symbol NOT IN ('005930', '000660', '042700', '069500', '122630', '068270', 
                                      '252670', '005380', '102110', '000270', '373220', '233740',
                                      '005490', '012330', '000100', '247540', '207940', '091230',
                                      '305540', '091180')
                GROUP BY symbol
                ORDER BY count DESC
            """)
            print(f"\nUS Symbols:")
            for s in us_symbols:
                print(f"  {s['symbol']}: {s['count']} ticks")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(check_us_data())
