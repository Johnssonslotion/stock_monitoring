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

from src.data_ingestion.price.common.kis_auth import KISAuthManager, get_kis_config
from src.api_gateway.rate_limiter import gatekeeper

logger = logging.getLogger("KISMinuteCollector")
logging.basicConfig(level=logging.INFO)

class KISMinuteCollector:
    """
    [RFC-008] Independent KIS Minute Data Collector for Verification
    """
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/stockval")
        self.auth_manager = KISAuthManager()
        self.config = get_kis_config()
        self.provider = "KIS"

    async def fetch_and_store(self, symbol: str, target_date: str):
        """
        Fetch minute candles for a symbol and date, then store in verification table.
        Args:
            symbol: Stock code (e.g., '005930')
            target_date: Date in YYYYMMDD format
        """
        # 1. Wait for Rate Limiter
        if not await gatekeeper.wait_acquire("KIS", timeout=10.0):
            logger.warning(f"[{symbol}] Rate limit timeout, skipping.")
            return

        # 2. Get Access Token
        try:
            token = await self.auth_manager.get_access_token()
        except Exception as e:
            logger.error(f"Failed to get KIS token: {e}")
            return

        # 3. Request Minute Data (TR: FHKST03010200)
        url = f"{self.config['base_url']}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        # TR ID handling (VTS vs Real)
        tr_id = "FHKST03010200"
        if "vts" in self.config['base_url'].lower():
            tr_id = "VTKST03010200"

        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.config.get('app_key') or "",
            "appsecret": self.config.get('app_secret') or "",
            "tr_id": tr_id,
            "custtype": "P",
            "User-Agent": "Mozilla/5.0"
        }
        params = {
            "fid_etc_cls_code": "",
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol,
            "fid_input_hour_1": target_date,
            "fid_pw_data_incu_yn": "Y"
        }

        async with aiohttp.ClientSession() as session:
            current_hour = target_date + "160000" # Start from market close
            total_fetched = 0
            
            for page in range(20): # Fetch up to 20 pages (enough for a day)
                params["fid_input_hour_1"] = current_hour[8:] # HHMMSS
                
                try:
                    async with session.get(url, headers=headers, params=params) as resp:
                        if resp.status != 200:
                            logger.error(f"[{symbol}] KIS API Error: {resp.status}, Body: {await resp.text()}")
                            break
                        
                        data = await resp.json()
                        if data.get("rt_cd") != "0":
                            logger.warning(f"[{symbol}] KIS Business Error: {data.get('msg1')}")
                            break
                        
                        output = data.get("output2", [])
                        if not output:
                            break
                        
                        await self._store_to_db(symbol, output)
                        total_fetched += len(output)
                        
                        # Get the earliest time in this batch to paginate further back
                        last_time = output[-1]["stck_cntg_hour"] # HHMMSS
                        if int(last_time) <= 90000: # Reached market open
                            break
                        
                        # Set next start hour (slightly before last_time to avoid overlap if needed, 
                        # but KIS usually handles it if fid_pw_data_incu_yn is N or similar)
                        current_hour = target_date + last_time
                        
                        # Respect rate limit between pages
                        await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"[{symbol}] Request failed: {e}")
                    break
            
            logger.info(f"[{symbol}] Total KIS candles fetched: {total_fetched}")

    async def _store_to_db(self, symbol: str, candles: List[dict]):
        conn = await asyncpg.connect(self.db_url)
        try:
            # Table: market_verification_raw (time, symbol, open, high, low, close, volume, provider)
            records = []
            for c in candles:
                # KIS: stck_bsop_date (YYYYMMDD), stck_cntg_hour (HHMMSS)
                dt_str = f"{c['stck_bsop_date']}{c['stck_cntg_hour'][:6]}"
                ts = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
                
                records.append((
                    ts,
                    symbol,
                    float(c['stck_oprc']),
                    float(c['stck_hgpr']),
                    float(c['stck_lwpr']),
                    float(c['stck_prpr']),
                    float(c['cntg_vol']),
                    self.provider
                ))
            
            # Use COPY for bulk insert
            await conn.copy_records_to_table(
                'market_verification_raw',
                records=records,
                columns=['time', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'provider']
            )
            logger.info(f"✅ [{symbol}] Saved {len(records)} KIS minute candles to TimescaleDB")
            
        except Exception as e:
            logger.error(f"[{symbol}] DB Store failed: {e}")
        finally:
            await conn.close()

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="005930")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()

    collector = KISMinuteCollector()
    await collector.fetch_and_store(args.symbol, args.date)

if __name__ == "__main__":
    asyncio.run(main())
