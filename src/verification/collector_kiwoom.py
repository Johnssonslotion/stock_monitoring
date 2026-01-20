print("BOOTING KIWOOM COLLECTOR...")
import asyncio
import os
import json
import logging
from datetime import datetime, timedelta
import aiohttp
import asyncpg
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import sys
from src.api_gateway.rate_limiter import gatekeeper

logger = logging.getLogger("KiwoomMinuteCollector")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class KiwoomMinuteCollector:
    """
    [RFC-008] Independent Kiwoom Minute Data Collector for Verification
    Uses ka10080 REST API.
    """
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        self.app_key = os.getenv("KIWOOM_APP_KEY")
        self.app_secret = os.getenv("KIWOOM_APP_SECRET")
        self.api_url = "https://api.kiwoom.com/api/dostk/chart"
        self.token_url = "https://api.kiwoom.com/oauth2/token"
        self.provider = "KIWOOM"
        self._token = None
        self._token_expire = None

    async def _get_token(self):
        """Kiwoom OAuth2 Token 발급 및 캐싱"""
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
                    logger.error(f"Kiwoom Token Error: {await resp.text()}")
                    raise Exception("Kiwoom Auth Failed")
                
                data = await resp.json()
                self._token = data.get("token")
                # 24시간 유효하나 안전하게 23시간 캐싱
                self._token_expire = datetime.now() + timedelta(hours=23)
                return self._token

    async def fetch_and_store(self, symbol: str, target_date: str):
        """
        Fetch minute candles for a symbol and date.
        target_date: YYYYMMDD
        """
        try:
            print(f"DEBUG: Start fetching for {symbol} on {target_date}")
            # 1. GateKeeper (Rate Limit)
            print("Requesting Rate Limit...")
            if not await gatekeeper.wait_acquire("KIWOOM", timeout=10.0):
                logger.warning(f"[{symbol}] Kiwoom Rate limit timeout.")
                print("Rate limit timeout")
                return
            print("Rate Limit Acquired.")

            # 2. Token
            print("Getting Token...")
            token = await self._get_token()
            print(f"Token acquired: {token[:10]}...")

            # 3. Request (ka10080)
            headers = {
                "api-id": "ka10080",
                "authorization": f"Bearer {token}",
                "content-yn": "N",
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": "Mozilla/5.0"
            }
            payload = {
                "stk_cd": symbol,
                "tic_scope": "1", # 1 minute
                "upd_stkpc_tp": "1"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers, ssl=False) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error(f"[{symbol}] Kiwoom API Error: {resp.status}, Body: {body}")
                        return
                    
                    data = await resp.json()
                    # Fix: Correct key is stk_min_pole_chart_qry (found via debug)
                    chart_data = data.get("stk_min_pole_chart_qry", [])
                    
                    if not chart_data:
                        logger.warning(f"[{symbol}] Kiwoom Data Missing. Full Response: {data}")
                        return
                    
                    # DEBUG: Print first item keys and values
                    logger.info(f"DEBUG [{symbol}] First Item Keys: {list(chart_data[0].keys())}")

                    filtered = []
                    for c in chart_data:
                        # Parsing cntr_tm: YYYYMMDDHHMMSS
                        cntr_tm = c.get("cntr_tm", "")
                        if not cntr_tm or len(cntr_tm) < 14:
                            continue
                        
                        row_date = cntr_tm[:8] # YYYYMMDD
                        if row_date == target_date:
                            filtered.append(c)

                    if not filtered:
                        logger.info(f"[{symbol}] No data for specific date {target_date} in response. Found: {len(chart_data)} records.")
                        return

                    await self._store_to_db(symbol, filtered)
                    
        except Exception as e:
            logger.error(f"[{symbol}] Kiwoom fetch failed: {e}", exc_info=True)

    async def _store_to_db(self, symbol: str, candles: List[dict]):
        conn = await asyncpg.connect(self.db_url)
        try:
            records = []
            for c in candles:
                try:
                    # Key mapping based on debug log
                    # {'cur_prc': '-145200', 'trde_qty': '1330940', 'cntr_tm': '20260120153000', 
                    #  'open_pric': '-145200', 'high_pric': '-145200', 'low_pric': '-145200', ...}
                    
                    price_key = "cur_prc"
                    open_key = "open_pric" 
                    high_key = "high_pric"
                    low_key = "low_pric"
                    vol_key = "trde_qty"
                    time_key = "cntr_tm" # YYYYMMDDHHMMSS

                    dt_str = c[time_key] # already YYYYMMDDHHMMSS
                    ts = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
                    
                    records.append((
                        ts,
                        symbol,
                        abs(float(c[open_key])),
                        abs(float(c[high_key])),
                        abs(float(c[low_key])),
                        abs(float(c[price_key])),
                        float(c[vol_key]),
                        self.provider
                    ))
                except KeyError as e:
                    logger.error(f"Missing key: {e}. Available keys: {list(c.keys())}")
                    continue
            
            await conn.copy_records_to_table(
                'market_verification_raw',
                records=records,
                columns=['time', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'provider']
            )
            logger.info(f"✅ [{symbol}] Saved {len(records)} Kiwoom minute candles to TimescaleDB")
            
        except Exception as e:
            logger.error(f"[{symbol}] Kiwoom DB Store failed: {e}")
        finally:
            await conn.close()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="005930")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()

    collector = KiwoomMinuteCollector()
    await collector.fetch_and_store(args.symbol, args.date)

if __name__ == "__main__":
    asyncio.run(main())
