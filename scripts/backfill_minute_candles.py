#!/usr/bin/env python3
"""
KIS API를 통한 1분봉 백필 스크립트

KIS API 제약사항:
- 1분봉은 최대 30일까지만 제공
- 분당 최대 20회 API 호출 제한
- TR_ID: FHKST03010200 (국내주식분봉조회)
"""
import asyncio
import asyncpg
import os
import yaml
import csv
from datetime import datetime, timedelta
from pathlib import Path
import logging
import sys
import httpx
from dotenv import load_dotenv

# .env.dev 로드
env_path = Path(__file__).parent.parent / '.env.dev'
load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class MinuteCandleBackfiller:
    def __init__(self):
        # TimescaleDB connection (Docker 기본 포트 5432)
        self.db_url = 'postgresql://postgres:password@localhost:5432/stockval'
        self.app_key = os.getenv('KIS_APP_KEY')
        self.app_secret = os.getenv('KIS_APP_SECRET')
        self.access_token = None
        self.symbols = self._load_symbols()
        
        # CSV for error records
        self.error_csv_path = Path(__file__).parent.parent / 'logs' / 'backfill_errors.csv'
        self.error_csv_path.parent.mkdir(exist_ok=True)
        self._init_error_csv()
    
    def _init_error_csv(self):
        """에러 CSV 파일 초기화"""
        if not self.error_csv_path.exists():
            with open(self.error_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'symbol', 'date', 'time_str', 'error', 'raw_data'])
    
    def _log_error_to_csv(self, symbol: str, date_str: str, time_str: str, error: str, candle: dict):
        """에러 데이터를 CSV에 저장"""
        try:
            with open(self.error_csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    symbol,
                    date_str,
                    time_str,
                    str(error),
                    str(candle)
                ])
        except Exception as e:
            logger.error(f"Failed to log error to CSV: {e}")
    
    async def get_access_token(self):
        """KIS API 액세스 토큰 발급"""
        if self.access_token:
            return self.access_token
        
        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=data)
            result = resp.json()
            self.access_token = result['access_token']
            logger.info("✅ KIS Access Token acquired")
            return self.access_token
        
    def _load_symbols(self):
        """configs/kr_symbols.yaml에서 종목 로드"""
        config_path = Path(__file__).parent.parent / 'configs' / 'kr_symbols.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        symbols = []
        # ETF/지수
        for item in config['symbols'].get('indices', []):
            symbols.append(item['symbol'])
        for item in config['symbols'].get('leverage', []):
            symbols.append(item['symbol'])
        
        # 개별 종목
        sectors = config['symbols'].get('sectors', {})
        for sector_name, sector_data in sectors.items():
            for item in sector_data.get('top3', []):
                symbols.append(item['symbol'])
        
        return symbols
    
    async def fetch_minute_candles(self, symbol: str, date: str):
        """
        특정 날짜의 1분봉 데이터 조회
        
        Args:
            symbol: 종목코드 (6자리)
            date: YYYYMMDD 형식
        """
        try:
            token = await self.get_access_token()
            
            url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
            
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": os.getenv('KIS_APP_KEY'),
                "appsecret": os.getenv('KIS_APP_SECRET'),
                "tr_id": "FHKST03010200",
                "custtype": "P"
            }
            
            params = {
                "fid_etc_cls_code": "",
                "fid_cond_mrkt_div_code": "J",  # 주식
                "fid_input_iscd": symbol,
                "fid_input_hour_1": date,  # YYYYMMDD
                "fid_pw_data_incu_yn": "Y"  # 데이터 연속 조회
            }
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"{symbol} {date}: HTTP {resp.status}")
                        return []
                    
                    data = await resp.json()
                    
                    if data.get('rt_cd') != '0':
                        logger.warning(f"{symbol} {date}: API Error {data.get('msg1')}")
                        return []
                    
                    output = data.get('output2', [])
                    logger.info(f"{symbol} {date}: {len(output)} candles fetched")
                    return output
                    
        except Exception as e:
            logger.error(f"{symbol} {date}: {e}")
            return []
    
    async def save_candles(self, conn, symbol: str, candles: list):
        """1분봉 데이터 DB 저장"""
        if not candles:
            return 0
        
        saved = 0
        for candle in candles:
            try:
                # KIS API 응답 포맷:
                # stck_bsop_date: 영업일자 (YYYYMMDD)
                # stck_cntg_hour: 시각 (HHMMSS)
                # stck_prpr: 현재가 (종가)
                # stck_oprc: 시가
                # stck_hgpr: 고가
                # stck_lwpr: 저가
                # cntg_vol: 체결거래량
                
                date_str = candle['stck_bsop_date']
                time_str = candle['stck_cntg_hour']
                
                # 타임스탬프 생성: YYYYMMDD + HHMMSS (마지막 2자리 초 제거)
                # KIS API는 HHMMSS00 형식 (마지막 00은 밀리초)
                time_clean = time_str[:6]  # HHMMSS만 사용
                timestamp = datetime.strptime(f"{date_str}{time_clean}", "%Y%m%d%H%M%S")
                
                await conn.execute("""
                    INSERT INTO market_candles (time, symbol, open, high, low, close, volume, interval)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, '1m')
                    ON CONFLICT (time, symbol, interval) DO NOTHING
                """,
                    timestamp,
                    symbol,
                    float(candle['stck_oprc']),
                    float(candle['stck_hgpr']),
                    float(candle['stck_lwpr']),
                    float(candle['stck_prpr']),
                    float(candle['cntg_vol'])
                )
                saved += 1
                
            except Exception as e:
                # 에러 데이터를 CSV에 저장
                self._log_error_to_csv(symbol, date_str, time_str, str(e), candle)
                continue
        
        return saved
    
    async def backfill_symbol(self, conn, symbol: str, days: int = 30):
        """
        특정 종목의 N일치 1분봉 백필
        
        Args:
            symbol: 종목코드
            days: 백필 일수 (최대 30)
        """
        logger.info(f"[{symbol}] Starting backfill for {days} days")
        
        total_saved = 0
        
        for day_offset in range(days):
            target_date = datetime.now() - timedelta(days=day_offset)
            date_str = target_date.strftime('%Y%m%d')
            
            # 주말 스킵
            if target_date.weekday() >= 5:  # 토(5), 일(6)
                logger.debug(f"[{symbol}] {date_str}: Weekend, skipping")
                continue
            
            candles = await self.fetch_minute_candles(symbol, date_str)
            saved = await self.save_candles(conn, symbol, candles)
            total_saved += saved
            
            logger.info(f"[{symbol}] {date_str}: {saved} candles saved")
            
            # API 레이트 리밋 준수 (분당 20회)
            await asyncio.sleep(3)  # 3초 대기 = 분당 20회
        
        logger.info(f"[{symbol}] Backfill complete: {total_saved} total candles")
        return total_saved
    
    async def run(self, days: int = 30):
        """전체 백필 실행"""
        logger.info(f"Starting 1-minute candle backfill for {len(self.symbols)} symbols, {days} days")
        
        conn = await asyncpg.connect(self.db_url)
        
        try:
            grand_total = 0
            
            for idx, symbol in enumerate(self.symbols, 1):
                logger.info(f"[{idx}/{len(self.symbols)}] Processing {symbol}...")
                
                total = await self.backfill_symbol(conn, symbol, days)
                grand_total += total
                
                # 종목간 대기 (API 부하 분산)
                if idx < len(self.symbols):
                    await asyncio.sleep(5)
            
            logger.info(f"✅ Backfill complete! {grand_total} total candles saved")
            
        finally:
            await conn.close()


async def main():
    backfiller = MinuteCandleBackfiller()
    await backfiller.run(days=30)


if __name__ == "__main__":
    asyncio.run(main())
