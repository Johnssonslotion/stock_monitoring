
import logging
import yaml
import os
from datetime import datetime
from src.core.schema import OrderbookData, OrderbookUnit
from src.data_ingestion.price.common.websocket_base import BaseCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KRASPCollector")

CONFIG_FILE = os.getenv("CONFIG_FILE", "configs/kr_symbols.yaml")

class KRASPCollector(BaseCollector):
    """한국 시장 실시간 호가 수집기 (핸들러)"""
    
    def __init__(self):
        super().__init__(market="KR", tr_id="H0STASP0")
        
    def get_channel(self) -> str:
        return "orderbook.kr"
    
    def load_symbols(self) -> list:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            symbols_config = config.get('symbols', {})
            targets = []
             
             # 1. 인덱스 대장주 (KODEX 200 등) - Top 1 only for now
            if 'indices' in symbols_config:
                for item in symbols_config['indices'][:1]:
                    targets.append(item['symbol'])
            
            # 2. 섹터별 1위
            if 'sectors' in symbols_config:
                for sector in symbols_config['sectors'].values():
                    if sector.get('top3'):
                        targets.append(sector['top3'][0]['symbol'])
            
            self.symbols = list(set(targets))
            logger.info(f"Loaded {len(self.symbols)} KR ASP symbols")
            return self.symbols
        except Exception as e:
            logger.error(f"Symbol Load Error: {e}")
            return []

    def parse_tick(self, body_str: str):
        # 호가 파싱
        fields = body_str.split('^')
        try:
            symbol = fields[0]
            
            asks = []
            bids = []
            
            for i in range(5):
                asks.append(OrderbookUnit(
                    price=float(fields[3+i]),
                    vol=float(fields[23+i])
                ))
                bids.append(OrderbookUnit(
                    price=float(fields[13+i]),
                    vol=float(fields[33+i])
                ))
                
            return OrderbookData(
                symbol=symbol,
                asks=asks,
                bids=bids
            )
            
        except Exception as e:
            logger.error(f"KR ASP Parse Error: {e}")
            return None
