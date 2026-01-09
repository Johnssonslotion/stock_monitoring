"""
한국 시장 실시간 데이터 수집기 (H0STCNT0)
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
logger = logging.getLogger("KRCollector")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KIS_WS_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:21000")
CONFIG_FILE = os.getenv("CONFIG_FILE", "configs/kr_symbols.yaml")


from src.data_ingestion.price.common.websocket_base import BaseCollector

class KRRealCollector(BaseCollector):
    """한국 시장 실시간 데이터 수집기 (핸들러)"""
    
    def __init__(self):
        super().__init__(market="KR", tr_id="H0STCNT0")
    
    def get_channel(self) -> str:
        return "ticker.kr"
    
    def load_symbols(self) -> list:
        """
        설정 파일로부터 수집 대상 한국 주식 종목 로드
        
        Returns:
            list: 종목 코드 리스트
        """
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
            CONFIG_FILE
        )
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        symbols_data = config.get('symbols', {})
        kr_targets = []
        
        # 지수 ETF
        for item in symbols_data.get('indices', []):
            kr_targets.append(item['symbol'])
        
        # 레버리지 ETF
        for item in symbols_data.get('leverage', []):
            kr_targets.append(item['symbol'])
        
        # 섹터별
        for sector_data in symbols_data.get('sectors', {}).values():
            kr_targets.append(sector_data['etf']['symbol'])
            for stock in sector_data.get('top3', []):
                kr_targets.append(stock['symbol'])
        
        self.symbols = list(set(kr_targets))
        logger.info(f"Loaded {len(self.symbols)} KR symbols from {CONFIG_FILE}")
        return self.symbols
    
    def parse_tick(self, body_str: str):
        """
        한국 시장 틱 데이터 파싱 (H0STCNT0)
        
        Args:
            body_str: WebSocket 메시지 body
            
        Returns:
            MarketData or None
        """
        fields = body_str.split('^')
        try:
            # KR Format: H0STCNT0
            # Field 0: 종목코드, Field 2: 현재가, Field 5: 전일대비, Field 7: 누적거래량
            return MarketData(
                symbol=fields[0],
                price=float(fields[2]),
                change=float(fields[5]),
                volume=float(fields[7]),
                timestamp=datetime.now()
            )
        except (IndexError, ValueError) as e:
            logger.error(f"KR Parsing Error: {e} | Raw: {body_str}")
            return None
    
