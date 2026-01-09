import asyncio
import asyncpg

async def check_jan5_samples():
    try:
        conn = await asyncpg.connect(
            user="postgres", 
            password="password", 
            database="stockval", 
            host="localhost"
        )
        
        # Get samples from Jan 5 successful collection
        samples = await conn.fetch("""
            SELECT time, symbol, price, volume, change
            FROM market_ticks
            WHERE time >= '2026-01-05 09:00:00+09'
              AND time <= '2026-01-05 15:30:00+09'
            ORDER BY time
            LIMIT 20
        """)
        
        print(f"=== Jan 5 Successful Data Samples ===")
        for s in samples:
            print(f"{s['time']} | {s['symbol']:10} | price:{s['price']:10.2f} | vol:{s['volume']:12.0f} | chg:{s['change']:6.2f}")
        
        # Get unique symbols from Jan 5
        symbols = await conn.fetch("""
            SELECT symbol, COUNT(*) as count
            FROM market_ticks
            WHERE time >= '2026-01-05 09:00:00+09'
              AND time <= '2026-01-05 15:30:00+09'
            GROUP BY symbol
            ORDER BY count DESC
        """)
        
        print(f"\n=== Jan 5 Symbols by Tick Count ===")
        for s in symbols:
            print(f"{s['symbol']:10}: {s['count']:,} ticks")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(check_jan5_samples())
