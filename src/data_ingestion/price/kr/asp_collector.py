
import logging
import yaml
import os
from datetime import datetime
from src.core.schema import OrderbookData, OrderbookUnit
from src.data_ingestion.price.common.websocket_base import BaseCollector

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logger = logging.getLogger("KRASPCollector")

CONFIG_FILE = os.getenv("CONFIG_FILE", "configs/kr_symbols.yaml")

class KRASPCollector(BaseCollector):
    """한국 시장 실시간 호가 수집기 (핸들러)"""
    
    def __init__(self):
        super().__init__(market="KR", tr_id="H0STASP0")
        
    def get_channel(self) -> str:
        return "orderbook.kr"
    
    def load_symbols(self) -> list:
        # Strategy Update (ISSUE-020): KIS Orderbook Disabled (Role Separation)
        # All Orderbook data is collected via Kiwoom.
        self.symbols = []
        logger.info("KIS Orderbook Collection Disabled (Strategy: Pure Role Separation)")
        return self.symbols


    def parse_tick(self, body_str: str):
        # 호가 파싱
        fields = body_str.split('^')
        try:
            symbol = fields[0]
            
            asks = []
            bids = []
            
            for i in range(5):
                asks.append(OrderbookUnit(
                    price=float(fields[3+i]),    # ASKP1~5: Index 3~7
                    vol=float(fields[21+i])      # ASKP_RSQN1~5: Index 21~25 (수정: 23→21)
                ))
                bids.append(OrderbookUnit(
                    price=float(fields[12+i]),   # BIDP1~5: Index 12~16 (수정: 13→12)
                    vol=float(fields[30+i])      # BIDP_RSQN1~5: Index 30~34 (수정: 33→30)
                ))
                
            return OrderbookData(
                symbol=symbol,
                asks=asks,
                bids=bids
            )
            
        except Exception as e:
            logger.error(f"KR ASP Parse Error: {e}")
            return None

    def parse_orderbook(self, body_str: str):
        """Test compatibility alias"""
        return self.parse_tick(body_str)
