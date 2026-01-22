
import asyncio
import asyncpg
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("CandleImputer")

class CandleImputer:
    """
    [RFC-009] Candle Imputation with Ground Truth Priority
    
    Priority Hierarchy:
    1. REST_API_KIS / REST_API_KIWOOM (Ground Truth)
    2. TICK_AGGREGATION_VERIFIED (Volume Check 통과)
    3. TICK_AGGREGATION_UNVERIFIED (미검증)
    """
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")

    async def impute_date(self, date_str: str):
        conn = await asyncpg.connect(self.db_url)
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            logger.info(f"🚀 Starting Candle Imputation for {date_str}")

            # 1. Fetch Log-based Candles (Base Layer)
            # Aggregating ticks from 'market_ticks_recovery' (and 'market_ticks_imputed' if we had any)
            # For now, focus on market_ticks_recovery as the primary LOG source.
            logger.info("   📥 Fetching Log-based Candles...")
            log_query = """
                SELECT 
                    time_bucket('1 minute', time) as minute,
                    symbol,
                    (array_agg(price ORDER BY time ASC))[1] as open,
                    MAX(price) as high,
                    MIN(price) as low,
                    (array_agg(price ORDER BY time DESC))[1] as close,
                    SUM(volume) as volume
                FROM market_ticks_recovery
                WHERE CAST(time AS DATE) = $1
                GROUP BY minute, symbol
            """
            log_rows = await conn.fetch(log_query, target_date)
            log_map = {(r['minute'], r['symbol']): r for r in log_rows}
            logger.info(f"      -> Loaded {len(log_map)} log-based candles.")

            # 2. Fetch Kiwoom Verification Candles (Imputation Layer)
            logger.info("   📥 Fetching Kiwoom Verification Candles...")
            kw_query = """
                SELECT 
                    time as minute,
                    symbol,
                    open, high, low, close, volume
                FROM market_verification_raw
                WHERE CAST(time AS DATE) = $1 AND provider = 'KIWOOM'
            """
            kw_rows = await conn.fetch(kw_query, target_date)
            kw_map = {(r['minute'], r['symbol']): r for r in kw_rows}
            logger.info(f"      -> Loaded {len(kw_map)} Kiwoom candles.")

            # 3. Merge & Decide
            logger.info("   🔄 Merging and Deciding Source...")
            merged_candles = []
            stats = {'LOG_AGG': 0, 'KIWOOM_IMPUTE': 0, 'TOTAL': 0}
            
            # Union of all keys
            all_keys = set(log_map.keys()) | set(kw_map.keys())
            
            for key in all_keys:
                minute, symbol = key
                log_c = log_map.get(key)
                kw_c = kw_map.get(key)
                
                final_c = None
                source = ""
                
                # Decision Logic
                if not log_c:
                    # Case A: Missing in Logs -> Use Kiwoom
                    final_c = kw_c
                    source = "KIWOOM_IMPUTE"
                elif not kw_c:
                    # Case B: Missing in Kiwoom (Rare) -> Use Log
                    final_c = log_c
                    source = "LOG_AGG"
                else:
                    # Case C: Both exist -> RFC-009 Ground Truth Priority
                    # Kiwoom REST API = Ground Truth (1순위)
                    # Log Aggregation = Needs verification (2/3순위)
                    
                    log_vol = log_c['volume']
                    kw_vol = kw_c['volume']
                    
                    # Volume Check for verification
                    if kw_vol > 0:
                        diff_pct = abs(log_vol - kw_vol) / kw_vol
                    else:
                        diff_pct = 0 if log_vol == 0 else 1.0
                    
                    # RFC-009: REST API (Kiwoom) is ALWAYS Ground Truth
                    # Use Kiwoom as final value, but mark Log as verified if within tolerance
                    final_c = kw_c
                    source = "REST_API_KIWOOM"  # Ground Truth
                    
                    # Log verification status for analytics (future use)
                    if diff_pct <= 0.001:  # 0.1% tolerance
                        logger.debug(f"[{symbol}] Tick aggregation VERIFIED (diff={diff_pct:.4f})")
                
                if final_c:
                    # RFC-009: Map legacy source names to standard source_type
                    source_type_map = {
                        'REST_API_KIWOOM': 'REST_API_KIWOOM',
                        'KIWOOM_IMPUTE': 'REST_API_KIWOOM',
                        'LOG_AGG': 'TICK_AGGREGATION_UNVERIFIED'
                    }
                    
                    merged_candles.append({
                        'time': final_c['minute'],
                        'symbol': final_c['symbol'],
                        'interval': '1m',
                        'open': float(final_c['open']),
                        'high': float(final_c['high']),
                        'low': float(final_c['low']),
                        'close': float(final_c['close']),
                        'volume': float(final_c['volume']),
                        'source_type': source_type_map.get(source, 'TICK_AGGREGATION_UNVERIFIED')
                    })
                    stats[source] += 1
                    stats['TOTAL'] += 1

            # 4. Upsert to market_candles
            logger.info(f"   💾 Upserting {len(merged_candles)} candles to 'market_candles'...")
            
            upsert_query = """
                INSERT INTO market_candles (time, symbol, interval, open, high, low, close, volume, source_type)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (time, symbol, interval) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    source_type = EXCLUDED.source_type;
            """
            
            # Batch insert
            batch_size = 5000
            for i in range(0, len(merged_candles), batch_size):
                batch = merged_candles[i:i+batch_size]
                data = [(c['time'], c['symbol'], '1m', c['open'], c['high'], c['low'], c['close'], c['volume'], c['source_type']) for c in batch]
                await conn.executemany(upsert_query, data)
                logger.info(f"      - Processed {i + len(batch)}/{len(merged_candles)}")

            logger.info("✅ Imputation Complete.")
            logger.info(f"   Summary: {stats}")

        finally:
            await conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    imputer = CandleImputer()
    asyncio.run(imputer.impute_date(args.date))
