
import asyncio
import os
import sys
import logging
import asyncpg
import httpx
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.data_ingestion.price.common.kis_auth import KISAuthManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataRecovery")

class DataRecoveryManager:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "password"),
            "database": os.getenv("DB_NAME", "stockval")
        }
        self.auth_manager = KISAuthManager()
        self.pool = None
        self.client = httpx.AsyncClient(timeout=10.0)
        self.cached_token = None
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.base_url = "https://openapi.koreainvestment.com:9443"

    async def connect_db(self):
        try:
            self.pool = await asyncpg.create_pool(**self.db_config)
            logger.info("✅ Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"DB Connection failed: {e}")
            raise

    async def get_target_symbols(self):
        # For now, target Samsung Electronics (005930) as pilot
        return ['005930']

    async def fetch_ticks(self, symbol: str, start_time_str: str, end_time_str: str):
        """
        Fetch ticks from KIS API (inquire-time-itemconclusion).
        Note: API returns data backwards from 'fid_input_hour_1'.
        We need to iterate until we cover the gap.
        """
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.cached_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010200", 
            "custtype": "P"
        }

        collected = []
        current_request_time = end_time_str # e.g. "120200"
        target_start = start_time_str # e.g. "100200"
        
        logger.info(f"📥 Fetching ticks for {symbol}: {target_start} ~ {current_request_time}")

        while True:
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol,
                "fid_input_hour_1": current_request_time
            }

            try:
                resp = await self.client.get(url, headers=headers, params=params)
                data = resp.json()
                
                if data.get('rt_cd') != '0':
                    logger.error(f"API Error: {data.get('msg1')}")
                    break
                
                ticks = data.get('output1', [])
                if not ticks:
                    break

                # Ticks are in Descending order (Latest first)
                new_batch = []
                reached_start = False
                
                for t in ticks:
                    t_time = t['stck_cntg_hour'] # HHMMSS
                    if t_time < target_start:
                        reached_start = True
                        continue # Skip older than start
                    if t_time > end_time_str:
                        continue # Skip newer than end (shouldnt happen given request logic)
                        
                    new_batch.append(t)
                
                collected.extend(new_batch)
                
                last_time_in_batch = ticks[-1]['stck_cntg_hour']
                
                if reached_start or last_time_in_batch < target_start:
                    logger.info("Reached start time.")
                    break
                    
                if last_time_in_batch >= current_request_time:
                     # No progress
                     break
                     
                current_request_time = last_time_in_batch
                await asyncio.sleep(0.1) # Rate limit

            except Exception as e:
                logger.error(f"Fetch Error: {e}")
                break
        
        return collected

    async def save_ticks(self, symbol: str, ticks: list, date_str: str):
        if not ticks:
            return
            
        logger.info(f"💾 Saving {len(ticks)} ticks to DB...")
        
        async with self.pool.acquire() as conn:
            # Prepare batch
            values = []
            for t in ticks:
                # KIS Time: HHMMSS -> Combine with Date
                # date_str: YYYYMMDD
                dt_str = f"{date_str}{t['stck_cntg_hour']}"
                dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
                # Add KST timezone info if needed, or assume DB uses UTC?
                # Usually TimescaleDB stores TIMESTAMPTZ. 
                # Assuming input is KST (UTC+9). 
                # Postgres expects ISO format.
                dt_iso = dt.isoformat() + "+09:00"
                
                values.append((
                    dt_iso,
                    symbol,
                    float(t['stck_prpr']),     # price
                    float(t['cntg_vol']),      # volume (transaction vol)
                    float(t['prdy_vrss']),     # change
                    'KIS',                     # source
                    dt_iso                     # received_time (approx)
                ))
            
            # Bulk Insert
            # Schema: time, symbol, price, volume, change, source, received_time
            # Verify schema matches Step 572
            # time, symbol, price, volume, change, broker, broker_time, received_time, sequence_number, source
            # We need to match columns safely.
            
            # Using COPY for speed or executemany
            query = """
            INSERT INTO market_ticks (time, symbol, price, volume, change, source, received_time, broker)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'KIS')
            ON CONFLICT DO NOTHING;
            """
            
            # ON CONFLICT might not work on hypertable without specific index.
            # But TimescaleDB allows duplicates usually unless constrained.
            # We assume simple insert.
            
            await conn.executemany(query, values)
            logger.info("✅ Saved completed.")

    async def run(self):
        await self.connect_db()
        
        # Authenticate
        self.cached_token = await self.auth_manager.get_access_token()
        if not self.cached_token:
            logger.error("Failed to get token")
            return

        symbols = await self.get_target_symbols()
        today_str = datetime.now().strftime("%Y%m%d")
        
        # Confirmed Gaps for 2026-01-19 (Today)
        # Gap 1: 09:00:00 ~ 09:40:00
        # Gap 2: 10:02:00 ~ 12:02:00
        gaps = [
            ("090000", "094000"),
            ("100200", "120200")
        ]
        
        for symbol in symbols:
            for start, end in gaps:
                logger.info(f"Recovering Gap {start}-{end} for {symbol}...")
                ticks = await self.fetch_ticks(symbol, start, end)
                await self.save_ticks(symbol, ticks, today_str)
        
        logger.info("🏁 All Recovery Tasks Completed.")

if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv() # Ensure env vars
    manager = DataRecoveryManager()
    asyncio.run(manager.run())
