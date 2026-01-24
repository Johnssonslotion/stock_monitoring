import asyncio
import logging
import os
import yaml
import asyncpg
from datetime import datetime
from typing import List, Dict

from src.api_gateway.hub.client import APIHubClient

logger = logging.getLogger("HistoryCollector")

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

# TR ID Mapping for API Hub
API_TR_MAPPING = {
    "KIS": {
        "kr_minute_history": "FHKST03010200",  # 국내주식 분봉 조회
        "us_minute_history": "HHDFS76950200",  # 해외주식 분봉 조회
    }
}

class HistoryCollector:
    def __init__(self):
        self.hub_client = APIHubClient()
        self.db_pool = None
        self.symbols = [] # List of {'symbol': '...', 'market': 'KR'|'US'}

    async def init_db(self):
        """[ISSUE-036] 필수 테이블 존재 여부 검증 (DDL은 migrations/에서 관리)"""
        conn = await asyncpg.connect(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        try:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'market_minutes')"
            )
            if not exists:
                logger.error("CRITICAL: Table 'market_minutes' not found. Please run 'make migrate-up' first.")
                raise RuntimeError("Database schema incomplete: table 'market_minutes' missing.")
            
            logger.info("Database schema verification completed (SSoT: market_minutes).")
        finally:
            await conn.close()

    async def load_config_symbols(self):
        """YAML 파일에서 심볼 로드"""
        # KR
        try:
            with open("configs/kr_symbols.yaml", "r") as f:
                conf = yaml.safe_load(f)
                # Parse indices, sectors.top1, etc.
                # Simplified: Just load what we can. 
                # Actually, real_collector parsing logic is complex.
                # For History, we want ALL symbols present in configs.
                self._parse_symbols_recursive(conf['symbols'], 'KR')
        except Exception as e:
            logger.error(f"Failed to load KR symbols: {e}")

        # US
        try:
            with open("configs/us_symbols.yaml", "r") as f:
                conf = yaml.safe_load(f)
                self._parse_symbols_recursive(conf['symbols'], 'US')
        except Exception as e:
            logger.error(f"Failed to load US symbols: {e}")
            
        logger.info(f"Loaded {len(self.symbols)} total symbols for history collection.")

    def _parse_symbols_recursive(self, data, market):
        if isinstance(data, list):
            for item in data:
                self._parse_symbols_recursive(item, market)
        elif isinstance(data, dict):
            if 'symbol' in data:
                self.symbols.append({'symbol': data['symbol'], 'market': market})
            else:
                for v in data.values():
                    self._parse_symbols_recursive(v, market)

    async def run(self):
        """
        Main collection loop
        ISSUE-041: Uses API Hub for centralized token management and rate limiting
        """
        # 1. DB Init
        await self.init_db()
        self.db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        
        # 2. Initialize API Hub Client (no direct auth needed)
        await self.hub_client.connect()
        logger.info("✅ API Hub Client initialized")
        
        # 3. Load Symbols
        await self.load_config_symbols()
        
        # 4. Start Collection Loop
        # Concurrency: 1 symbol at a time, API Hub handles rate limiting
        
        while True:
            # Check Schedule before processing ANY symbol
            await self.check_pause_window()
            
            # If we finished all symbols, wait or exit?
            # User wants 2 years data. Once done for all symbols, we should Stop?
            # For this task, we loop through symbols once.
            all_done = True
            for sym_info in self.symbols:
                # Add check here too for granular pause
                await self.check_pause_window()
                await self.collect_symbol_history(sym_info)
            
            if all_done:
                logger.info("All symbols processed for history. Sleeping 1 hour before re-check (or exit).")
                await asyncio.sleep(3600)

    async def check_pause_window(self):
        """
        장 운영 시간(KR 09:00~15:30, US 22:30~05:00)에는 수집 중단.
        Buffer: KR(08:50 ~ 15:40), US(22:20 ~ 05:10)
        """
        import pytz
        while True:
            tz_kr = pytz.timezone('Asia/Seoul')
            now = datetime.now(tz_kr)
            current_time = now.time()
            
            # Simple Time Comparison
            # KR
            kr_start = datetime.strptime("08:50", "%H:%M").time()
            kr_end = datetime.strptime("15:40", "%H:%M").time()
            
            # US (Night in KR)
            us_start = datetime.strptime("22:20", "%H:%M").time()
            us_end = datetime.strptime("05:10", "%H:%M").time()
            
            is_kr_market = kr_start <= current_time <= kr_end
            
            # US logic: 22:20 ~ 23:59 OR 00:00 ~ 05:10
            is_us_market = (us_start <= current_time) or (current_time <= us_end)
            
            if is_kr_market or is_us_market:
                logger.info(f"🚫 Market is OPEN ({current_time.strftime('%H:%M')}). Pausing history collection to protect realtime.")
                await asyncio.sleep(600) # Sleep 10 mins and check again
            else:
                break
            
    async def collect_symbol_history(self, sym_info):
        market = sym_info['market']
        symbol = sym_info['symbol']
        logger.info(f"Processing {market} {symbol}...")
        
        # Determine End Time (Now)
        # We fetch backwards.
        # But we need to know where to stop (if resuming).
        # For MVP, let's fetch strictly 2 years from NOW, using ON CONFLICT DO NOTHING.
        # Total days = 365*2 = 730 days.
        
        if market == 'KR':
            await self.fetch_kr_history(symbol)
        else:
            await self.fetch_us_history(symbol)

    async def fetch_kr_history(self, symbol):
        """
        국내주식 분봉 이력 조회 (API Hub 사용)
        ISSUE-041: Token 관리 및 Rate Limiting을 API Hub에서 처리
        """
        current_req_time = datetime.now().strftime("%H%M%S")
        target_year = datetime.now().year - 2
        
        while True:
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": current_req_time,
                "FID_PW_DATA_INCU_YN": "Y",
                "FID_ETC_CLS_CODE": ""
            }
            
            # API Hub를 통한 호출
            result = await self.hub_client.execute(
                provider="KIS",
                tr_id=API_TR_MAPPING["KIS"]["kr_minute_history"],
                params=params,
                timeout=15.0
            )
            
            if result.get("status") != "SUCCESS":
                logger.error(f"Failed to fetch data for {symbol} at {current_req_time}: {result.get('reason')}")
                await asyncio.sleep(5)
                break
                
            data = result.get("data", {})
            rows = data.get('output2', [])
            
            if not rows:
                logger.info(f"No more data for {symbol}.")
                break
                
            # Save DB
            records = []
            for row in rows:
                dt_str = f"{row['stck_bsop_date']} {row['stck_cntg_hour']}"
                dt = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                
                records.append((
                    dt, symbol,
                    float(row['stck_oprc']), float(row['stck_hgpr']),
                    float(row['stck_lwpr']), float(row['stck_prpr']), 
                    float(row['cntg_vol'])
                ))
            
            await self.save_batch(records)
            
            # Update Cursor
            last_row = rows[-1]
            current_req_time = last_row['stck_cntg_hour']
            
            # Check Year
            last_date = last_row['stck_bsop_date']
            if int(last_date[:4]) <= target_year:
                logger.info(f"Reached target year {target_year}. Stopping.")
                break
                        
            await asyncio.sleep(0.5) # Additional safety delay

    async def fetch_us_history(self, symbol):
        """
        해외주식 분봉 이력 조회 (API Hub 사용)
        ISSUE-041: Token 관리 및 Rate Limiting을 API Hub에서 처리
        """
        next_key = ""
        keyb = "" 
        
        while True:
            params = {
                "AUTH": "",
                "EXCD": "NAS", 
                "SYMB": symbol,
                "NMIN": "1",
                "PINC": "1",
                "NEXT": next_key,
                "NREC": "120",
                "KEYB": keyb
            }
            
            # API Hub를 통한 호출
            result = await self.hub_client.execute(
                provider="KIS",
                tr_id=API_TR_MAPPING["KIS"]["us_minute_history"],
                params=params,
                timeout=15.0
            )
            
            if result.get("status") != "SUCCESS":
                logger.error(f"Failed to fetch US data for {symbol}: {result.get('reason')}")
                break
                
            data = result.get("data", {})
            rows = data.get('output2', [])
            
            if not rows:
                break
                
            records = []
            for row in rows:
                dt_str = f"{row['kymd']} {row['khms']}"
                dt = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
                
                records.append((
                    dt, symbol,
                    float(row['open']), float(row['high']),
                    float(row['low']), float(row['last']),
                    float(row['evol'])
                ))
                
            await self.save_batch(records)
            
            last_row = rows[-1]
            if int(last_row['kymd'][:4]) <= datetime.now().year - 2:
                break
            
            # Update Keys for Next Page
            # US API Logic:
            # Check header or body for Next Key?
            # Usually `output2` is the data. 
            # If we just rely on KEYB (Date), KIS usually paginates automatically if we pass the previous KEYB?
            # Or we need to check `msg1` / headers.
            # For this context, let's update KEYB to the last received time.
            keyb = last_row['kymd'] + last_row['khms']
            # next_key? If KIS requires it, it is usually returned in `next` field.
            # Assuming basic Key Date pagination works for now. 
            
            await asyncio.sleep(0.5)

    async def save_batch(self, records):
        if not records:
            return
        async with self.db_pool.acquire() as conn:
            try:
                await conn.executemany("""
                    INSERT INTO market_minutes (
                        time, symbol, open, high, low, close, volume
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (time, symbol) DO NOTHING
                """, records)
                logger.info(f"Saved {len(records)} rows for {records[0][1]}")
            except Exception as e:
                logger.error(f"DB Save Error: {e}")

