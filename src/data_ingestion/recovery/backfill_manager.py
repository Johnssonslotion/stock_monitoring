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
    def __init__(self, target_symbols: Optional[List[str]] = None):
        self.auth_manager = KISAuthManager()
        self.symbols = target_symbols if target_symbols else self._load_symbols()
        
        # Create temp DB path with timestamp
        self.timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.db_filename = f"recovery_temp_{self.timestamp_str}.duckdb"
        self.db_path = os.path.join(OUTPUT_DIR, self.db_filename)
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self._init_db()

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
        # For fuller coverage, we would need 30s intervals or handle exact time cursors
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
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get('output1', [])
                        if items:
                            for item in items:
                                tick_time_str = item['stck_cntg_hour']
                                # Format: YYYY-MM-DD HH:MM:SS
                                timestamp = f"{today_str} {tick_time_str[:2]}:{tick_time_str[2:4]}:{tick_time_str[4:6]}"
                                
                                tick = {
                                    'symbol': symbol,
                                    'timestamp': timestamp,
                                    'price': float(item['stck_prpr']),
                                    'volume': int(item['cntg_vol']),
                                    'source': 'KIS_REST_RECOVERY',
                                    'execution_no': f"{timestamp}_{item['cntg_vol']}" # Synthetic ID
                                }
                                all_ticks.append(tick)
                        
                        # Rate Limit Prevention (KIS: ~20 TPS per key)
                        await asyncio.sleep(0.06) 
                        
                    else:
                        logger.warning(f"[{symbol}] Failed {t_time}: HTTP {resp.status}")
                        await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"[{symbol}] Error at {t_time}: {e}")
                await asyncio.sleep(0.5)

        if not all_ticks:
            logger.warning(f"[{symbol}] No ticks recovered.")
            return

        # Save to DuckDB immediately to free memory
        try:
            df = pd.DataFrame(all_ticks).drop_duplicates(subset=['timestamp', 'execution_no'])
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
        logger.info(f"🚀 Starting Tick Recovery for {len(self.symbols)} symbols...")
        logger.info(f"💾 Temporary DB: {self.db_path}")
        
        token = await self.auth_manager.get_access_token()
        if not token:
            logger.error("❌ Failed to get access token.")
            return

        async with aiohttp.ClientSession() as session:
            # Chunking symbols to avoid overwhelming everything, although basic loop is sequential per symbol
            # Implementing simple parallelism for symbols (e.g. batch of 5)
            batch_size = 5
            for i in range(0, len(self.symbols), batch_size):
                batch = self.symbols[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: {batch}")
                tasks = [self.fetch_real_ticks(session, sym, token) for sym in batch]
                await asyncio.gather(*tasks)

        print(f"OUTPUT_DB={self.db_path}") # stdout for pipe

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='KIS Tick Data Recovery')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to recover')
    args = parser.parse_args()

    manager = BackfillManager(target_symbols=args.symbols)
    asyncio.run(manager.run())
