
import asyncio
import os

import redis.asyncio as redis
from datetime import datetime, timedelta
import logging

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DB_NAME = "stockval"

async def check_redis_flow():
    """Check if Redis channel has activity (by subscribing briefly or checking stats)"""
    # Redis stats are hard to poll for "last 5 min volume" without a listener.
    # Instead, we check DB (Timescale/DuckDB) for recent rows.
    # Or Sentinel logs.
    pass

def check_timescale_recent(minutes=5):
    """Check TimescaleDB for rows in last N minutes"""
    # We execute psql command via docker usually, but here we might be inside or outside.
    # Assuming this runs on host, use docker exec.
    cmd = f"""docker exec stock-timescale psql -U postgres -d stockval -t -c "SELECT count(*) FROM market_ticks WHERE time >= NOW() - INTERVAL '{minutes} minutes'; " """
    import subprocess
    try:
        result = subprocess.check_output(cmd, shell=True).decode().strip()
        count = int(result) if result else 0
        return count
    except Exception as e:
        print(f"Timescale Check Error: {e}")
        return -1

def check_duckdb_recent(minutes=5):
    # If using DuckDB
    pass

async def main():
    print(f"[{datetime.now()}] 🛡️ Starting Real-time Flow Verification (Last 5 min)...")
    
    # 1. TimescaleDB Check (Ticks)
    tick_count = check_timescale_recent(5)
    
    if tick_count > 0:
        print(f"✅ [PASS] TimescaleDB: {tick_count} ticks received in last 5 min.")
    else:
        print(f"❌ [FAIL] TimescaleDB: No ticks in last 5 min! (Count: {tick_count})")
        
    
    # 2. Backfill Status (Jan 13 US Data)
    # Check total rows for US market on Jan 13 main session
    cmd_backfill = """docker exec stock-timescale psql -U postgres -d stockval -t -c "SELECT count(*) FROM market_candles WHERE time >= '2026-01-13 14:30:00' AND time <= '2026-01-13 21:00:00';" """
    try:
        import subprocess
        result_bf = subprocess.check_output(cmd_backfill, shell=True).decode().strip()
        bf_count = int(result_bf) if result_bf else 0
        print(f"📊 [BACKFILL] Jan 13 US Data Count: {bf_count}")
        
        # Check specific symbol AAPL
        cmd_aapl = """docker exec stock-timescale psql -U postgres -d stockval -t -c "SELECT count(*) FROM market_candles WHERE time >= '2026-01-13 14:30:00' AND time <= '2026-01-13 21:00:00' AND symbol = 'AAPL';" """
        result_aapl = subprocess.check_output(cmd_aapl, shell=True).decode().strip()
        aapl_count = int(result_aapl) if result_aapl else 0
        print(f"   - AAPL Count: {aapl_count}")
        
    except Exception as e:
        print(f"Backfill Check Error: {e}")
    
if __name__ == "__main__":
    asyncio.run(main())
