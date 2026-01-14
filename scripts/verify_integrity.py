import asyncio
import asyncpg
import os
from datetime import datetime
import json

# DB Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

async def verify_integrity():
    conn = await asyncpg.connect(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
    )
    
    print("="*60)
    print(" 🛠️  DATA INTEGRITY VERIFICATION REPORT")
    print(f" 📅  Time: {datetime.now()}")
    print("="*60)
    
    # 1. Real-Time Data Verification (market_ticks)
    print("\n[1] Real-Time Data (market_ticks)")
    try:
        # Check total count
        total_ticks = await conn.fetchval("SELECT count(*) FROM market_ticks")
        
        # Check latest tick
        latest = await conn.fetchrow("SELECT time, symbol, price FROM market_ticks ORDER BY time DESC LIMIT 1")
        
        print(f"  - Total Ticks Received: {total_ticks:,}")
        if latest:
            print(f"  - Latest Tick: {latest['time']} | {latest['symbol']} | {latest['price']}")
            delta = (datetime.now(latest['time'].tzinfo) - latest['time']).total_seconds()
            if delta < 60:
                print(f"  - Status: ✅ LIVE (Last tick {delta:.1f}s ago)")
            else:
                print(f"  - Status: ⚠️ DELAYED (Last tick {delta:.1f}s ago)")
                
        # Group by symbol (top 5 by count)
        top_symbols = await conn.fetch("""
            SELECT symbol, count(*) as cnt 
            FROM market_ticks 
            WHERE time > NOW() - INTERVAL '1 hour'
            GROUP BY symbol 
            ORDER BY cnt DESC 
            LIMIT 5
        """)
        print("  - Recent Activity (Last 1hr Top 5):")
        for row in top_symbols:
            print(f"    - {row['symbol']}: {row['cnt']:,} ticks")
            
    except Exception as e:
        print(f"  - Error: {e}")

    # 2. Historical Data Verification (market_candles)
    print("\n[2] Historical Data (market_candles)")
    try:
        # Check total daily candles
        daily_count = await conn.fetchval("SELECT count(*) FROM market_candles WHERE interval = '1d'")
        minute_count = await conn.fetchval("SELECT count(*) FROM market_candles WHERE interval = '1m'")
        
        print(f"  - Total Daily Records (2Y Backfill): {daily_count:,}")
        print(f"  - Total Minute Records: {minute_count:,}")
        
        # Verify specific symbol (e.g., 005930 - Samsung Electronics)
        target = "005930"
        stats = await conn.fetchrow("""
            SELECT count(*) as cnt, min(time) as start, max(time) as end 
            FROM market_candles 
            WHERE symbol = $1 AND interval = '1d'
        """, target)
        
        if stats:
            print(f"  - [{target}] Daily Stats:")
            print(f"    - Count: {stats['cnt']} (Expected: ~480+ for 2 years)")
            print(f"    - Range: {stats['start'].date()} ~ {stats['end'].date()}")
            
            if stats['cnt'] > 450:
                 print(f"    - Status: ✅ VALID (Sufficient history for {target})")
            else:
                 print(f"    - Status: ⚠️ INSUFFICIENT (Check backfill logs)")
                 
    except Exception as e:
         print(f"  - Error: {e}")

    print("\n" + "="*60)
    await conn.close()

if __name__ == "__main__":
    asyncio.run(verify_integrity())
