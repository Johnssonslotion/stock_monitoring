import asyncio
import asyncpg
import os
import logging
import yaml
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv
from src.data_ingestion.price.common.kis_auth import KISAuthManager, get_kis_config
from src.api_gateway.rate_limiter import gatekeeper

# Load environment variables
load_dotenv()

logger = logging.getLogger("OutlierRecoveryKIS")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class OutlierTickRecovery:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        self.auth_manager = KISAuthManager()
        self.config = get_kis_config()
        self.base_url = self.config['base_url']
        # TR ID handling
        self.tr_id = "FHKST01010400"
        if "vts" in self.base_url.lower():
            self.tr_id = "VTKST01010300" # Not sure if VTS supports this TR, fallback might be needed

    async def run(self, date_str: str):
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # 1. Identify Outliers (Log Vol vs API Vol Mismatch)
            # We focus on cases where Log is missing or significantly less than API
            logger.info(f"🔍 Identifying outliers for {date_str}...")
            
            # Using market_verification_raw (Step 2 Result) vs market_ticks_recovery (Step 1 Result)
            query = """
                WITH logs AS (
                    SELECT 
                        time_bucket('1 minute', time) as minute,
                        symbol,
                        sum(volume) as volume
                    FROM market_ticks_recovery
                    WHERE CAST(time AS DATE) = $1
                    GROUP BY 1, 2
                ),
                api AS (
                    SELECT 
                        time as minute,
                        symbol,
                        volume
                    FROM market_verification_raw
                    WHERE CAST(time AS DATE) = $1
                )
                SELECT 
                    a.symbol, 
                    a.minute, 
                    a.volume as api_vol, 
                    COALESCE(l.volume, 0) as log_vol
                FROM api a
                LEFT JOIN logs l ON a.minute = l.minute AND a.symbol = l.symbol
                WHERE 
                    COALESCE(l.volume, 0) = 0  -- Completely missing in logs
                    OR ABS(a.volume - COALESCE(l.volume, 0)) > (a.volume * 0.1) -- >10% mismatch
                ORDER BY a.symbol, a.minute
            """
            rows = await conn.fetch(query, target_date)
            logger.info(f"📋 Found {len(rows)} outlier minutes to recover.")

            # 2. Group by Symbol for efficient processing
            tasks_by_symbol = {}
            for r in rows:
                sym = r['symbol']
                if sym not in tasks_by_symbol:
                    tasks_by_symbol[sym] = []
                tasks_by_symbol[sym].append(r['minute'])

            # 3. Process Recovery
            token = await self.auth_manager.get_access_token()
            if not token:
                logger.error("❌ Failed to get access token")
                return

            async with aiohttp.ClientSession() as session:
                total_recovered = 0
                for i, (symbol, minutes) in enumerate(tasks_by_symbol.items(), 1):
                    logger.info(f"[{i}/{len(tasks_by_symbol)}] Recovering {symbol} ({len(minutes)} slots)...")
                    
                    # Process minutes for this symbol
                    ticks = await self._recover_symbol_ticks(session, token, symbol, minutes, date_str)
                    if ticks:
                        await self._save_ticks(conn, ticks)
                        total_recovered += len(ticks)
                    
                    # Symbol-level rate limit buffer
                    await asyncio.sleep(0.5)

            logger.info(f"✅ Recovery Complete. Total Ticks Recovered: {total_recovered}")

        finally:
            await conn.close()

    async def _recover_symbol_ticks(self, session, token, symbol, minutes, date_str):
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.config['app_key'],
            "appsecret": self.config['app_secret'],
            "tr_id": self.tr_id,
            "custtype": "P"
        }
        
        recovered_ticks = []
        
        # Sort minutes to process sequentially
        minutes.sort()
        
        # We need to query by minute. The API takes specific time input.
        # Strategically, if we query 'HHMM00', it usually returns ticks *before* that time?
        # No, 'inquire-time-itemconclusion' usually returns ticks starting from input hour backwards.
        # But wait, typically you ask for '100000' and it gives you ticks like 09:59:59...
        # So if we want minute '09:00', we might need to ask for '090100'?
        # Let's try querying exactly the minute time 'HHMM00' and check results.
        # Actually, standard behavior is: Input '090100' -> Returns ticks for 09:00 (approx).
        # We will iterate the targets.
        
        for dt_min in minutes:
            # We want to cover the minute described by dt_min
            # e.g., if dt_min is 09:00, we want execution times 09:00:00 ~ 09:00:59
            # If we request '090100', we likely get 09:00 data.
            target_time_req = (dt_min + timedelta(minutes=1)).strftime("%H%M%S")
            
            # Retry loop for rate limits
            max_retries = 3
            for attempt in range(max_retries):
                # Rate Limit Check
                if not await gatekeeper.wait_acquire("KIS", timeout=10.0):
                   logger.warning("Rate limit timeout")
                   await asyncio.sleep(1.0)
                   continue

                params = {
                    "fid_cond_mrkt_div_code": "J",
                    "fid_input_iscd": symbol,
                    "fid_input_hour_1": target_time_req 
                }

                if minutes.index(dt_min) == 0 and attempt == 0:
                     masked_headers = headers.copy()
                     masked_headers['authorization'] = 'Bearer ***'
                     masked_headers['appkey'] = (masked_headers['appkey'][:4] + '***') if masked_headers.get('appkey') else 'None'
                     masked_headers['appsecret'] = '***'
                     # logger.info(f"DEBUG HEADERS: {masked_headers}")

                try:
                    async with session.get(url, headers=headers, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            items = data.get('output1', [])
                            if not items:
                                logger.info(f"[{symbol}] No items in output1 for {target_time_req}")
                                break # No data for this minute, stop retrying

                            # DEBUG: Print first item time to verify format
                            first_time = items[0]['stck_cntg_hour']
                            logger.info(f"[{symbol}] Target: {target_time_req}, FirstItem: {first_time}, Count: {len(items)}")

                            for item in items:
                                t_str = item['stck_cntg_hour']
                                t_hhmm = t_str[:4]
                                expected_hhmm = dt_min.strftime("%H%M")
                                
                                # Exact minute match only
                                if t_hhmm == expected_hhmm:
                                    tick_dt_str = f"{date_str.replace('-','')} {t_str}"
                                    tick_dt = datetime.strptime(tick_dt_str, "%Y%m%d %H%M%S")
                                    
                                    recovered_ticks.append({
                                        'time': tick_dt,
                                        'symbol': symbol,
                                        'price': float(item['stck_prpr']),
                                        'volume': int(item['cntg_vol']),
                                        'source': 'KIS',
                                        'execution_no': f"{t_str}_{item['cntg_vol']}_{item['cntg_gval']}",
                                        'imputed_from': 'KIS_API'
                                    })
                            break # Success, exit retry loop
                        
                        else:
                            text = await resp.text()
                            if "EGW00201" in text or resp.status == 429:
                                logger.warning(f"Rate Limit Hit ({symbol} {target_time_req}), retrying ({attempt+1}/{max_retries})...")
                                await asyncio.sleep(1.0 * (attempt + 1)) # Backoff
                                continue
                            else:
                                logger.error(f"API Error {symbol} {target_time_req}: {resp.status} - {text}")
                                break # Non-retryable error

                except Exception as e:
                    logger.error(f"Fetch failed {symbol} {target_time_req}: {e}")
                    break
                
            # Internal tiny sleep (Conservative 2 TPS to avoid EGW00201)
            await asyncio.sleep(0.5)
            
        return recovered_ticks

    async def _save_ticks(self, conn, ticks: List[Dict]):
        if not ticks: return
        
        # Deduplication happens via ON CONFLICT usually, but copy_records is faster.
        # But we need ON CONFLICT. So use execute_many or individual inserts?
        # Given volume, Copy is best, but checks are hard.
        # Let's use INSERT ON CONFLICT DO NOTHING.
        
        insert_query = """
            INSERT INTO market_ticks_imputed (time, symbol, price, volume, source, execution_no, imputed_from)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (time, symbol, source, execution_no) DO NOTHING
        """
        
        data = [
            (t['time'], t['symbol'], t['price'], t['volume'], t['source'], t['execution_no'], t['imputed_from'])
            for t in ticks
        ]
        
        await conn.executemany(insert_query, data)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    recovery = OutlierTickRecovery()
    asyncio.run(recovery.run(args.date))
