
import logging
import yaml
import os
from datetime import datetime
from src.core.schema import OrderbookData, OrderbookUnit
from src.data_ingestion.price.common.websocket_base import BaseCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("USASPCollector")

CONFIG_FILE = os.getenv("CONFIG_FILE", "configs/us_symbols.yaml")

class USASPCollector(BaseCollector):
    """미국 시장 실시간 호가 수집기 (핸들러)"""
    
    def __init__(self):
        super().__init__(market="US", tr_id="HHDFS76200100") # 실시간 미국주식 호가 (User Confirmed)

    def get_channel(self) -> str:
        return "orderbook.us"

    def load_symbols(self) -> list:
        """대표 종목 하나(NVDA)만 수집 (User Request)"""
        # NVDA is NASDAQ -> DNAS Prefix
        self.symbols = ["DNASNVDA"]
        logger.info(f"Loaded {len(self.symbols)} US ASP symbols: {self.symbols}")
        return self.symbols

    def parse_tick(self, body_str: str):
        # 호가 파싱
        # Fields separated by ^
        fields = body_str.split('^')
        try:
            # HDFSASP0 fields:
            # [1]: symbol
            # [10]~[13]: Ask1 Price, Ask1 Vol, Bid1 Price, Bid1 Vol? 
            # NO. Original Code: 
            # Ask Price: 10 + i*4
            # Ask Vol: 11 + i*4
            # Bid Price: 12 + i*4
            # Bid Vol: 13 + i*4
            # Let's trust original code logic.
            
            symbol = fields[1]
            
            asks = []
            bids = []
            
            for i in range(5):
                offset = i * 4
                asks.append(OrderbookUnit(
                    price=float(fields[10 + offset]),
                    vol=float(fields[11 + offset])
                ))
                bids.append(OrderbookUnit(
                    price=float(fields[12 + offset]),
                    vol=float(fields[13 + offset])
                ))
                
            return OrderbookData(
                symbol=symbol,
                asks=asks,
                bids=bids
            )
            
        except Exception as e:
            logger.error(f"US ASP Parse Error: {e} | len={len(fields)}")
            return None
