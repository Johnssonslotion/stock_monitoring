import os
import logging
import asyncio
import asyncpg
import duckdb
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger("CrossChecker")
logging.basicConfig(level=logging.INFO)

class CrossChecker:
    """
    [RFC-008] 3-Way Consistency Check
    DuckDB Aggregated Ticks vs KIS REST vs Kiwoom REST
    """
    def __init__(self, duckdb_path: str = "data/ticks.duckdb", tsdb_url: str = None):
        self.duckdb_path = duckdb_path
        self.tsdb_url = tsdb_url or os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")

    async def run_check(self, symbol: str, date_str: str):
        """
        Compare data for a specific symbol and date.
        date_str: YYYY-MM-DD
        """
        logger.info(f"🔍 Starting Cross-Check for {symbol} on {date_str}")
        
        # 1. Aggregate DuckDB Ticks to Minutes
        local_minutes = self._aggregate_duckdb(symbol, date_str)
        if not local_minutes:
            logger.warning(f"[{symbol}] No local tick data found for {date_str}")
        
        # 2. Fetch API Data from TimescaleDB
        api_data = await self._fetch_tsdb_verification(symbol, date_str)
        
        # 3. Merge and Compare
        results = self._compare_sources(local_minutes, api_data, symbol, date_str)
        
        # 4. Store Results in TimescaleDB
        await self._store_results(results)
        
        # 5. Summary Report
        self._print_summary(symbol, results)

    def _aggregate_duckdb(self, symbol: str, date_str: str) -> Dict[str, Dict]:
        """Aggregate 1-minute OHLCV from market_ticks table in DuckDB"""
        try:
            conn = duckdb.connect(self.duckdb_path, read_only=True)
            # Filter for date
            query = f"""
                SELECT 
                    time_bucket(INTERVAL '1 minute', timestamp) as minute,
                    first(price) as open,
                    max(price) as high,
                    min(price) as low,
                    last(price) as close,
                    sum(volume) as volume
                FROM market_ticks
                WHERE symbol = '{symbol}'
                AND CAST(timestamp AS DATE) = '{date_str}'
                GROUP BY minute
                ORDER BY minute
            """
            df = conn.execute(query).df()
            conn.close()
            
            res = {}
            for _, row in df.iterrows():
                ts_key = row['minute'].isoformat()
                res[ts_key] = {
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": float(row['volume'])
                }
            return res
        except Exception as e:
            logger.error(f"DuckDB Aggregation failed: {e}")
            return {}

    async def _fetch_tsdb_verification(self, symbol: str, date_str: str) -> Dict[str, Dict[str, Dict]]:
        """Fetch raw verification data from TimescaleDB grouped by provider"""
        conn = await asyncpg.connect(self.tsdb_url)
        try:
            query = """
                SELECT time, provider, open, high, low, close, volume
                FROM market_verification_raw
                WHERE symbol = $1 AND CAST(time AS DATE) = $2
            """
            rows = await conn.fetch(query, symbol, datetime.strptime(date_str, "%Y-%m-%d").date())
            
            res = {}
            for r in rows:
                prov = r['provider']
                ts_key = r['time'].isoformat().replace("+00:00", "") # Normalize
                if prov not in res: res[prov] = {}
                res[prov][ts_key] = {
                    "open": r['open'], "high": r['high'], "low": r['low'], "close": r['close'], "volume": r['volume']
                }
            return res
        finally:
            await conn.close()

    def _compare_sources(self, local: Dict, api: Dict, symbol: str, date_str: str) -> List[Dict]:
        """Compare Local vs KIS vs Kiwoom"""
        all_timestamps = set(local.keys())
        for prov in api.values():
            all_timestamps.update(prov.keys())
        
        results = []
        for ts_str in sorted(list(all_timestamps)):
            # Normalize timestamp to naive for comparison or handle offset
            ts = datetime.fromisoformat(ts_str.replace("+00:00", ""))
            
            l = local.get(ts_str) or local.get(ts.isoformat()) or {}
            kis = api.get("KIS", {}).get(ts_str) or api.get("KIS", {}).get(ts.isoformat()) or {}
            kiwoom = api.get("KIWOOM", {}).get(ts_str) or api.get("KIWOOM", {}).get(ts.isoformat()) or {}
            
            status = "MATCH"
            res = {
                "time": ts,
                "symbol": symbol,
                "local_close": l.get("close"),
                "kis_close": kis.get("close"),
                "kiwoom_close": kiwoom.get("close"),
                "local_vol": l.get("volume"),
                "kis_vol": kis.get("volume"),
                "kiwoom_vol": kiwoom.get("volume"),
            }
            
            # Calculate Deltas
            if res["kis_close"] is not None and res["local_close"] is not None:
                res["price_delta_kis"] = abs(res["kis_close"] - res["local_close"])
                res["vol_delta_kis"] = abs(res.get("kis_vol", 0) - res.get("local_vol", 0))
            
            if res["kiwoom_close"] is not None and res["local_close"] is not None:
                res["price_delta_kiwoom"] = abs(res["kiwoom_close"] - res["local_close"])
                res["vol_delta_kiwoom"] = abs(res.get("kiwoom_vol", 0) - res.get("local_vol", 0))

            # Status determination
            if res["local_close"] is None:
                status = "MISSING_LOCAL"
            elif res["kis_close"] is None and res["kiwoom_close"] is None:
                status = "MISSING_API"
            else:
                # We have both Local and at least one API
                is_mismatch = False
                if res["kis_close"] is not None:
                    if abs(res["kis_close"] - res["local_close"]) > 0.1:
                        is_mismatch = True
                if res["kiwoom_close"] is not None:
                    if abs(res["kiwoom_close"] - res["local_close"]) > 0.1:
                        is_mismatch = True
                
                if is_mismatch:
                    status = "MISMATCH"
                else:
                    status = "MATCH"
            
            res["status"] = status
            results.append(res)
            
        return results

    async def _store_results(self, results: List[Dict]):
        if not results: return
        conn = await asyncpg.connect(self.tsdb_url)
        try:
            columns = [
                'time', 'symbol', 'local_close', 'kis_close', 'kiwoom_close',
                'local_vol', 'kis_vol', 'kiwoom_vol',
                'price_delta_kis', 'price_delta_kiwoom', 'vol_delta_kis', 'vol_delta_kiwoom',
                'status'
            ]
            records = []
            for r in results:
                records.append(tuple(r.get(col) for col in columns))
            
            # Upsert logic would be better but for now let's just insert
            await conn.execute("DELETE FROM market_verification_results WHERE symbol = $1 AND CAST(time AS DATE) = $2", 
                             results[0]['symbol'], results[0]['time'].date())
            
            await conn.copy_records_to_table('market_verification_results', records=records, columns=columns)
            logger.info(f"✅ Stored {len(records)} verification results to TimescaleDB")
        finally:
            await conn.close()

    def _print_summary(self, symbol: str, results: List[Dict]):
        total = len(results)
        matches = len([r for r in results if r['status'] == 'MATCH'])
        mismatches = len([r for r in results if r['status'] == 'MISMATCH'])
        missing_db = len([r for r in results if r['status'] == 'MISSING_LOCAL'])
        missing_api = len([r for r in results if r['status'] == 'MISSING_API'])
        
        print("\n" + "="*50)
        print(f"📊 Verification Summary for {symbol}")
        print("="*50)
        print(f"Total Minutes: {total}")
        print(f"Matches:       {matches} ({matches/total*100 if total > 0 else 0:.1f}%)")
        print(f"Mismatches:    {mismatches}")
        print(f"Missing (Local): {missing_db}")
        print(f"Missing (API):   {missing_api}")
        print("="*50)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="005930")
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    checker = CrossChecker()
    asyncio.run(checker.run_check(args.symbol, args.date))
