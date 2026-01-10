"""
미국 시장 실시간 데이터 수집기 (HDFSCNT0)
"""
import asyncio
import logging
import os
import yaml
import redis.asyncio as redis
from datetime import datetime, timedelta
from src.core.schema import MarketData
from src.data_ingestion.price.common import KISAuthManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("USCollector")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KIS_WS_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:21000")
CONFIG_FILE = os.getenv("CONFIG_FILE", "configs/us_symbols.yaml")


from src.data_ingestion.price.common.websocket_base import BaseCollector

class USRealCollector(BaseCollector):
    """미국 시장 실시간 데이터 수집기 (핸들러)"""
    TR_ID = "HDFSCNT0" # 실시간 미국주식 체결가 (Verified: HDFSCNT0 works with DNASAAPL)
    # Note: 200(Details), 100(Hoga). 300 is correct for Ticks.
    
    def __init__(self):
        super().__init__(market="US", tr_id=self.TR_ID)
    
    def get_channel(self) -> str:
        return "ticker.us"

    def load_symbols(self) -> list:
        """
        설정 파일로부터 수집 대상 미국 주식 종목 로드
        
        Returns:
            list: 종목 코드 리스트 (prefix 포함: NASAAPL, NYSSPY 등)
        """
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
            CONFIG_FILE
        )
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        symbols_data = config.get('symbols', {})
        us_targets = []
        
        # 거래소 prefix 결정 (NYS 또는 NAS)
        def get_prefix(exchange_name: str) -> str:
            # 설정 파일의 exchange 필드 사용 (기본값 NASDAQ)
            if not exchange_name:
                return "DNAS"
            
            ex = exchange_name.upper()
            if "NYSE" in ex:
                return "DNYS"
            elif "NASDAQ" in ex:
                return "DNAS"
            elif "AMEX" in ex:
                return "DAMS"
            else:
                return "DNAS" # Fallback
        
        # 지수 ETF
        for item in symbols_data.get('indices', []):
            prefix = get_prefix(item.get('exchange'))
            us_targets.append(f"{prefix}{item['symbol']}")
        
        # 레버리지 ETF
        for item in symbols_data.get('leverage', []):
            prefix = get_prefix(item.get('exchange'))
            us_targets.append(f"{prefix}{item['symbol']}")
        
        # 섹터별
        for sector_data in symbols_data.get('sectors', {}).values():
            etf = sector_data['etf']
            prefix = get_prefix(etf.get('exchange'))
            us_targets.append(f"{prefix}{etf['symbol']}")
            
            for stock in sector_data.get('top3', []):
                prefix = get_prefix(stock.get('exchange'))
                us_targets.append(f"{prefix}{stock['symbol']}")
        
        self.symbols = list(set(us_targets))
        logger.info(f"Loaded {len(self.symbols)} US symbols from {CONFIG_FILE}")
        return self.symbols
    
    def parse_tick(self, body_str: str):
        """
        미국 시장 틱 데이터 파싱 (HDFSCNT0)
        
        Args:
            body_str: WebSocket 메시지 body
            
        Returns:
            MarketData or None
        """
        fields = body_str.split('^')
        try:
            # US Format: HDFSCNT0
            # Field 1: 심볼, Field 11: 가격, Field 13: 거래량
            return MarketData(
                symbol=fields[1],
                price=float(fields[11]),
                change=0.0,
                volume=float(fields[13]),
                timestamp=datetime.now()
            )
        except (IndexError, ValueError) as e:
            logger.error(f"US Parsing Error: {e} | Raw: {body_str}")
            return None
    
