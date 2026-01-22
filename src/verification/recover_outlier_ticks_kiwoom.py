
import asyncio
import asyncpg
import os
import aiohttp
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Set
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("OutlierRecoveryKiwoom")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from src.api_gateway.rate_limiter import gatekeeper

class KiwoomTickRecovery:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        self.app_key = os.getenv("KIWOOM_APP_KEY")
        self.app_secret = os.getenv("KIWOOM_APP_SECRET")
        self.api_url = "https://api.kiwoom.com/api/dostk/chart" # ka10079
        self.token_url = "https://api.kiwoom.com/oauth2/token"
        
        self._token = None
        self._token_expire = None

    async def _get_token(self):
        if self._token and self._token_expire and datetime.now() < self._token_expire:
            return self._token

        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, json=payload, headers=headers, ssl=False) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Token Error: {text}")
                    return None
                data = await resp.json()
                self._token = data.get("token")
                expires_in = int(data.get("expires_in", 3600))
                self._token_expire = datetime.now() + timedelta(seconds=expires_in - 60)
                logger.info(f"Token acquired. Expires in {expires_in}s")
                return self._token

    async def run(self, date_str: str):
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        conn = await asyncpg.connect(self.db_url)
        
        try:
            # 1. Identify Outliers (Prioritizing Missing Logs vs Kiwoom Minute)
            logger.info(f"🔍 Identifying outliers for {date_str} based on Kiwoom data...")
            
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
                    WHERE CAST(time AS DATE) = $1 AND provider = 'KIWOOM'
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
                ORDER BY a.symbol DESC, a.minute DESC -- Descending to help backwards scan optimization?
            """
            rows = await conn.fetch(query, target_date)
            logger.info(f"📋 Found {len(rows)} outlier minutes to recover.")

            # Group by symbol
            tasks_by_symbol = {}
            for r in rows:
                sym = r['symbol']
                if sym not in tasks_by_symbol:
                    tasks_by_symbol[sym] = set()
                # Store HHMM string
                tasks_by_symbol[sym].add(r['minute'].strftime("%H%M"))

            # 2. Process Recovery
            token = await self._get_token()
            if not token: return

            async with aiohttp.ClientSession() as session:
                for i, (symbol, target_minutes_hhmm) in enumerate(tasks_by_symbol.items(), 1):
                    logger.info(f"[{i}/{len(tasks_by_symbol)}] Recovering {symbol} ({len(target_minutes_hhmm)} slots)...")
                    
                    ticks = await self._fetch_ticks_with_pagination(session, token, symbol, target_minutes_hhmm, date_str)
                    if ticks:
                        await self._save_ticks(conn, ticks)
                        logger.info(f"   Saved {len(ticks)} ticks for {symbol}")
                    
                    # Symbol-level rate limit buffer
                    await asyncio.sleep(0.5)

        finally:
            await conn.close()

    async def _fetch_ticks_with_pagination(self, session, token, symbol, target_minutes: Set[str], date_str):
        all_ticks = []
        next_key = None
        cont_yn = "N"
        
        # Sort targets to know when to stop (earliest time)
        sorted_targets = sorted(list(target_minutes))
        if not sorted_targets: return []
        earliest_target_hhmm = sorted_targets[0]
        
        max_pages = 50 # Limit to prevent infinite loops
        
        for page in range(max_pages):
            # Rate Limit
            if not await gatekeeper.wait_acquire("KIWOOM", timeout=10.0):
                logger.warning("Rate limit timeout")
                await asyncio.sleep(1.0)
                continue

            headers = {
                "api-id": "ka10079", # Stock Tick Chart Query
                "authorization": f"Bearer {token}",
                "content-yn": cont_yn,
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": "Mozilla/5.0"
            }
            if next_key:
                headers["next-key"] = next_key
                
            payload = {
                "stk_cd": symbol,
                "tic_scope": "1", # 1 tick
                "upd_stkpc_tp": "1"
            }
            
            # Retry loop for 429
            retry_count = 0
            max_retries = 5
            success = False
            
            while retry_count < max_retries:
                async with session.post(self.api_url, json=payload, headers=headers, ssl=False) as resp:
                    if resp.status == 200:
                        success = True
                        next_key = resp.headers.get("next-key")
                        data = await resp.json()
                        break
                    elif resp.status == 429 or resp.status == 503:
                        retry_wait = 2 * (retry_count + 1)
                        logger.warning(f"Rate Limit 429/503 for {symbol}. Sleeping {retry_wait}s...")
                        await asyncio.sleep(retry_wait)
                        retry_count += 1
                        continue
                    else:
                        logger.error(f"API Error {symbol}: {resp.status} {await resp.text()}")
                        return all_ticks # Stop processing this symbol on fatal error

            if not success:
                logger.error(f"Failed to fetch {symbol} after retries.")
                break

            # Process Data (moved inside loop in previous code, but now after success)
            # data is available here
                # Key might be stk_tic_chart_qry or similar (Need to be flexible based on minute api experience)
                # Minute was stk_min_pole_chart_qry. Tick might be different.
                # Helper function to find listing key
                items = []
                for k in data.keys():
                    if isinstance(data[k], list):
                        items = data[k]
                        break
                
                if not items:
                    break

                # Process Items (Latest to Oldest)
                last_time_hhmm = ""
                
                for item in items:
                    tm = item.get("cntr_tm", "")[:6] # HHMMSS
                    if not tm: continue
                    hhmm = tm[:4]
                    last_time_hhmm = hhmm
                    
                    # Filtering: Only keep if it matches one of our target minutes
                    if hhmm in target_minutes:
                         # Construct Tick Object
                         # date_str YYYY-MM-DD + tm HHMMSS
                         tick_dt = datetime.strptime(f"{date_str} {tm}", "%Y-%m-%d %H%M%S")
                         
                         all_ticks.append({
                             'time': tick_dt,
                             'symbol': symbol,
                             'price': float(item.get('cur_prc', 0)),
                             'volume': float(item.get('trde_qty', 0)),
                             'source': 'KIWOOM',
                             'execution_no': f"{tm}_{item.get('trde_qty')}", # Simple unique ID logic
                             'imputed_from': 'KIWOOM_API'
                         })
                
                # Check termination condition
                # If the last item's time is BEFORE our earliest target, we can stop.
                # (Assuming returned order is DESC time)
                if last_time_hhmm and last_time_hhmm < earliest_target_hhmm:
                    # logger.info(f"Reached {last_time_hhmm}, earlier than target {earliest_target_hhmm}. Stopping.")
                    break
                
                if not next_key:
                    break
                    
                cont_yn = "Y" # Next page

        return all_ticks

    async def _save_ticks(self, conn, ticks: List[Dict]):
        if not ticks: return
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
    from datetime import timedelta
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-01-20")
    args = parser.parse_args()
    
    recovery = KiwoomTickRecovery()
    asyncio.run(recovery.run(args.date))
