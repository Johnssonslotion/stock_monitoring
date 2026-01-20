import asyncio
import asyncpg
import os
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("RecoveryTriangulation")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class RecoveryTriangulator:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")

    async def run_triangulation(self, symbol: str, date_str: str):
        conn = await asyncpg.connect(self.db_url)
        try:
            logger.info(f"🔍 Triangulating {symbol} on {date_str}")
            
            # 1. Aggregate ticks from recovery table to minute bars
            # We group by source because we want to see if one source matches API better
            query = """
                WITH aggregated AS (
                    SELECT 
                        time_bucket('1 minute', time) as minute,
                        symbol,
                        source,
                        (array_agg(price ORDER BY time ASC))[1] as open,
                        max(price) as high,
                        min(price) as low,
                        (array_agg(price ORDER BY time DESC))[1] as close,
                        sum(volume) as volume,
                        count(*) as tick_count
                    FROM market_ticks_recovery
                    WHERE symbol = $1 AND CAST(time AS DATE) = $2
                    GROUP BY minute, symbol, source
                )
                SELECT 
                    a.minute,
                    a.source as recovery_source,
                    a.open as rec_open,
                    a.high as rec_high,
                    a.low as rec_low,
                    a.close as rec_close,
                    a.volume as rec_volume,
                    v.provider as api_provider,
                    v.open as api_open,
                    v.high as api_high,
                    v.low as api_low,
                    v.close as api_close,
                    v.volume as api_volume
                FROM aggregated a
                FULL OUTER JOIN market_verification_raw v 
                    ON a.minute = v.time 
                    AND a.symbol = v.symbol
                WHERE (a.symbol = $1 OR v.symbol = $1)
                ORDER BY a.minute ASC, a.source ASC;
            """
            
            rows = await conn.fetch(query, symbol, datetime.strptime(date_str, "%Y-%m-%d").date())
            
            matches = 0
            mismatches = 0
            missing_rec = 0
            missing_api = 0
            
            print(f"\n--- Triangulation Results for {symbol} ({date_str}) ---")
            print(f"{'Minute':<20} | {'Rec_Src':<8} | {'Status':<12} | {'Price Delta (C)':<15} | {'Vol Delta':<15}")
            print("-" * 85)
            
            for r in rows:
                minute = r['minute']
                if not r['rec_close']:
                    missing_rec += 1
                    status = "MISSING_REC"
                elif not r['api_close']:
                    missing_api += 1
                    status = "MISSING_API"
                else:
                    p_delta = abs(r['rec_close'] - r['api_close'])
                    v_delta = abs(r['rec_volume'] - r['api_volume'])
                    
                    if p_delta == 0 and v_delta == 0:
                        matches += 1
                        status = "MATCH"
                    else:
                        mismatches += 1
                        status = "MISMATCH"
                        
                    print(f"{str(minute):<20} | {r['recovery_source']:<8} | {status:<12} | {p_delta:<15} | {v_delta:<15}")

            print("-" * 85)
            print(f"Summary: Matches={matches}, Mismatches={mismatches}, MissingRecovery={missing_rec}, MissingAPI={missing_api}")
            
        finally:
            await conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    triangulator = RecoveryTriangulator()
    asyncio.run(triangulator.run_triangulation(args.symbol, args.date))
