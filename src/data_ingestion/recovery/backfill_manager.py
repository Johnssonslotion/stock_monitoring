"""
BackfillManager - 틱 데이터 복구 관리자

API Hub Queue 기반으로 REST API 호출을 중앙 집중화.

Reference:
    - ISSUE-040: API Hub v2 Phase 2 - Real API Integration
    - RFC-009: Ground Truth & API Control Policy
"""
import asyncio
import os
import yaml
import logging
import argparse
from datetime import datetime
import aiohttp
import pandas as pd
from typing import List, Dict, Optional
import duckdb
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

from src.data_ingestion.price.common import KISAuthManager
from src.api_gateway.rate_limiter import gatekeeper
from src.api_gateway.hub.client import APIHubClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BackfillManager")

# Constants
BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
OUTPUT_DIR = "data/recovery"
SYMBOLS_FILE = "configs/kr_symbols.yaml"

class BackfillManager:
    """
    틱 데이터 복구 관리자

    Args:
        target_symbols: 복구 대상 종목 코드 리스트
        use_hub: API Hub Queue 사용 여부 (기본: True)
    """

    def __init__(
        self,
        target_symbols: Optional[List[str]] = None,
        use_hub: bool = True
    ):
        self.auth_manager = KISAuthManager()
        self.symbols = target_symbols if target_symbols else self._load_symbols()
        self.use_hub = use_hub
        self.hub_client: Optional[APIHubClient] = None

        # Create temp DB path with timestamp
        self.timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.db_filename = f"recovery_temp_{self.timestamp_str}.duckdb"
        self.db_path = os.path.join(OUTPUT_DIR, self.db_filename)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self._self_diagnosis()  # RFC-009: Fail-Fast on missing config
        self._init_db()

        if self.use_hub:
            logger.info("🔗 API Hub mode enabled - using centralized Queue")

    def _self_diagnosis(self):
        """
        [RFC-009] Self-Diagnosis Entry: 필수 환경변수 검증.
        실패 시 즉시 종료하여 좀비 프로세스 방지.
        """
        required_vars = ["KIS_APP_KEY", "KIS_APP_SECRET", "KIS_BASE_URL"]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logger.critical(f"❌ SELF-DIAGNOSIS FAILED: Missing env vars: {missing}")
            logger.critical("Exiting immediately to prevent zombie process.")
            import sys
            sys.exit(1)
        logger.info("✅ Self-Diagnosis passed: All required env vars present.")

    def _init_db(self):
        conn = duckdb.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_ticks (
                symbol VARCHAR,
                timestamp TIMESTAMP,
                price DOUBLE,
                volume INT,
                source VARCHAR,
                execution_no VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.close()
        logger.info(f"Initialized temporary DB: {self.db_path}")

    def _load_symbols(self) -> List[str]:
        def extract_symbols(data):
            symbols = []
            if isinstance(data, dict):
                for k, v in data.items():
                    if k == 'symbol' and isinstance(v, str):
                        symbols.append(v)
                    else:
                        symbols.extend(extract_symbols(v))
            elif isinstance(data, list):
                for item in data:
                    symbols.extend(extract_symbols(item))
            return symbols

        try:
            with open(SYMBOLS_FILE, 'r') as f:
                config = yaml.safe_load(f)
                all_symbols = extract_symbols(config)
                return sorted(list(set(all_symbols)))
        except Exception as e:
            logger.error(f"Failed to load symbols: {e}")
            return []

    def detect_gaps(self, main_db_path: str = "data/ticks.duckdb", 
                   target_date: str = None, 
                   start_hour: int = 9, 
                   end_hour: int = 15) -> List[Dict]:
        """
        [ISSUE-031] Detect missing tick data gaps by querying main DuckDB.
        Returns list of missing minute ranges per symbol.
        
        Args:
            main_db_path: Path to main DuckDB file
            target_date: Date in YYYYMMDD format (default: today)
            start_hour: Market start hour (default: 9)
            end_hour: Market end hour (default: 15)
        
        Returns:
            List[Dict]: [{"symbol": "005930", "missing_minutes": ["09:00", "09:01", ...]}, ...]
        """
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        else:
            # Convert YYYYMMDD to YYYY-MM-DD
            target_date = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:8]}"
        
        try:
            conn = duckdb.connect(main_db_path, read_only=True)
            
            gaps = []
            for symbol in self.symbols:
                # Query existing minutes for this symbol on target date
                query = f"""
                    SELECT DISTINCT 
                        strftime(timestamp, '%H:%M') as minute
                    FROM market_ticks
                    WHERE symbol = '{symbol}'
                    AND DATE(timestamp) = '{target_date}'
                    ORDER BY minute
                """
                result = conn.execute(query).fetchall()
                existing_minutes = set([row[0] for row in result])
                
                # Generate expected minutes (market hours)
                expected_minutes = []
                for hour in range(start_hour, end_hour + 1):
                    for minute in range(60):
                        if hour == 15 and minute > 30:  # Market closes at 15:30
                            break
                        expected_minutes.append(f"{hour:02d}:{minute:02d}")
                
                missing = [m for m in expected_minutes if m not in existing_minutes]
                
                if missing:
                    gaps.append({
                        "symbol": symbol,
                        "date": target_date,
                        "missing_minutes": missing,
                        "total_missing": len(missing)
                    })
            
            conn.close()
            logger.info(f"🔍 Gap Detection: {len(gaps)} symbols have missing data")
            return gaps
            
        except Exception as e:
            logger.error(f"❌ Gap detection failed: {e}")
            return []

    async def fetch_real_ticks(self, session: aiohttp.ClientSession, symbol: str, token: str):
        """
        Fetch TICK Data using 'inquire-time-itemconclusion' (TR: FHKST01010300)

        API Hub 모드 또는 레거시 직접 호출 모드 지원.
        """
        if self.use_hub:
            return await self._fetch_ticks_via_hub(symbol)
        else:
            return await self._fetch_ticks_direct(session, symbol, token)

    async def _fetch_ticks_via_hub(self, symbol: str):
        """
        API Hub Queue를 통한 틱 데이터 조회

        ISSUE-040: 중앙 집중화된 API 호출
        """
        # Sampling Strategy: Every 1 minute from 15:30 to 09:00
        target_times = []
        curr = datetime.strptime("153000", "%H%M%S")
        end = datetime.strptime("090000", "%H%M%S")

        while curr >= end:
            target_times.append(curr.strftime("%H%M%S"))
            curr = curr - pd.Timedelta(minutes=1)

        today_str = datetime.now().strftime("%Y-%m-%d")
        all_ticks = []

        for t_time in target_times:
            try:
                # API Hub 통해 요청
                result = await self.hub_client.execute(
                    provider="KIS",
                    tr_id="FHKST01010300",
                    params={
                        "symbol": symbol,
                        "time": t_time
                    },
                    timeout=15.0
                )

                if result.get("status") == "SUCCESS":
                    data = result.get("data", {})
                    items = data.get("data", [])  # 정규화된 응답 구조

                    for item in items:
                        tick_time_str = item.get('stck_cntg_hour', t_time)
                        timestamp = f"{today_str} {tick_time_str[:2]}:{tick_time_str[2:4]}:{tick_time_str[4:6]}"

                        tick = {
                            'symbol': symbol,
                            'timestamp': timestamp,
                            'price': float(item.get('stck_prpr', 0)),
                            'volume': int(item.get('cntg_vol', 0)),
                            'source': 'REST_API_KIS',  # RFC-009: Ground Truth
                            'execution_no': f"{timestamp}_{item.get('cntg_vol', 0)}"
                        }
                        all_ticks.append(tick)

                elif result.get("status") == "RATE_LIMITED":
                    logger.warning(f"[{symbol}] Rate limited at {t_time}, skipping")
                    continue
                else:
                    logger.warning(
                        f"[{symbol}] Failed {t_time}: {result.get('reason')}"
                    )

            except TimeoutError:
                logger.warning(f"[{symbol}] Timeout at {t_time}, skipping")
            except Exception as e:
                logger.error(f"[{symbol}] Error at {t_time}: {e}")

        self._save_ticks(symbol, all_ticks)

    async def _fetch_ticks_direct(
        self, session: aiohttp.ClientSession, symbol: str, token: str
    ):
        """
        레거시 직접 API 호출 (gatekeeper 사용)

        use_hub=False일 때 호출됨.
        """
        url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": "FHKST01010300",
            "custtype": "P"
        }

        # Sampling Strategy: Every 1 minute from 15:30 to 09:00
        target_times = []
        curr = datetime.strptime("153000", "%H%M%S")
        end = datetime.strptime("090000", "%H%M%S")

        while curr >= end:
            target_times.append(curr.strftime("%H%M%S"))
            curr = curr - pd.Timedelta(minutes=1)

        today_str = datetime.now().strftime("%Y-%m-%d")
        all_ticks = []

        for t_time in target_times:
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": t_time
            }

            try:
                # RFC-009: Use gatekeeper for centralized rate limiting
                if not await gatekeeper.wait_acquire("KIS", timeout=10.0):
                    logger.warning(f"[{symbol}] Rate limit timeout at {t_time}, skipping")
                    continue

                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get('output1', [])
                        if items:
                            for item in items:
                                tick_time_str = item['stck_cntg_hour']
                                timestamp = f"{today_str} {tick_time_str[:2]}:{tick_time_str[2:4]}:{tick_time_str[4:6]}"

                                tick = {
                                    'symbol': symbol,
                                    'timestamp': timestamp,
                                    'price': float(item['stck_prpr']),
                                    'volume': int(item['cntg_vol']),
                                    'source': 'REST_API_KIS',  # RFC-009: Ground Truth
                                    'execution_no': f"{timestamp}_{item['cntg_vol']}"
                                }
                                all_ticks.append(tick)

                    else:
                        logger.warning(f"[{symbol}] Failed {t_time}: HTTP {resp.status}")
                        await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"[{symbol}] Error at {t_time}: {e}")
                await asyncio.sleep(0.5)

        self._save_ticks(symbol, all_ticks)

    def _save_ticks(self, symbol: str, all_ticks: list):
        """틱 데이터 DuckDB 저장"""
        if not all_ticks:
            logger.warning(f"[{symbol}] No ticks recovered.")
            return

        try:
            df = pd.DataFrame(all_ticks).drop_duplicates(
                subset=['timestamp', 'execution_no']
            )
            conn = duckdb.connect(self.db_path)
            conn.executemany("""
                INSERT INTO market_ticks (symbol, timestamp, price, volume, source, execution_no)
                VALUES (?, ?, ?, ?, ?, ?)
            """, df[['symbol', 'timestamp', 'price', 'volume', 'source', 'execution_no']].values.tolist())
            conn.close()
            logger.info(f"[{symbol}] ✅ Recovered {len(df)} ticks")
        except Exception as e:
            logger.error(f"[{symbol}] Database Error: {e}")

    async def run(self):
        """
        틱 데이터 복구 실행

        API Hub 모드 또는 레거시 모드로 실행.
        """
        logger.info(f"🚀 Starting Tick Recovery for {len(self.symbols)} symbols...")
        logger.info(f"💾 Temporary DB: {self.db_path}")
        logger.info(f"🔗 Mode: {'API Hub' if self.use_hub else 'Legacy Direct'}")

        if self.use_hub:
            # API Hub 모드
            async with APIHubClient() as hub_client:
                self.hub_client = hub_client

                # 배치 처리 (API Hub가 Rate Limit 관리)
                batch_size = 5
                for i in range(0, len(self.symbols), batch_size):
                    batch = self.symbols[i:i+batch_size]
                    logger.info(f"Processing batch {i//batch_size + 1}: {batch}")
                    tasks = [self.fetch_real_ticks(None, sym, None) for sym in batch]
                    await asyncio.gather(*tasks)

        else:
            # 레거시 모드 (직접 호출 + gatekeeper)
            token = await self.auth_manager.get_access_token()
            if not token:
                logger.error("❌ Failed to get access token.")
                return

            async with aiohttp.ClientSession() as session:
                batch_size = 5
                for i in range(0, len(self.symbols), batch_size):
                    batch = self.symbols[i:i+batch_size]
                    logger.info(f"Processing batch {i//batch_size + 1}: {batch}")
                    tasks = [self.fetch_real_ticks(session, sym, token) for sym in batch]
                    await asyncio.gather(*tasks)

        print(f"OUTPUT_DB={self.db_path}")  # stdout for pipe

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='KIS Tick Data Recovery')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to recover')
    parser.add_argument(
        '--use-hub',
        action='store_true',
        default=True,
        help='Use API Hub Queue (default: True)'
    )
    parser.add_argument(
        '--legacy',
        action='store_true',
        help='Use legacy direct API calls (disables Hub mode)'
    )
    args = parser.parse_args()

    # --legacy 플래그로 Hub 모드 비활성화
    use_hub = not args.legacy

    manager = BackfillManager(target_symbols=args.symbols, use_hub=use_hub)
    asyncio.run(manager.run())
