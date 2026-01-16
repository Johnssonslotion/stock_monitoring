import random
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Type, List
from pydantic import BaseModel
from src.data_ingestion.price.schemas.mirae import MiraeWSResponse, MiraePriceData
from src.data_ingestion.price.schemas.kiwoom_re import KiwoomRealData

logger = logging.getLogger(__name__)

class MockDataProvider:
    """
    브로커 시뮬레이션을 위한 모킹 데이터 생성기
    """
    @staticmethod
    def generate_mirae_tick(symbol: str) -> Dict[str, Any]:
        """미래에셋 실시간 체결 데이터 모킹"""
        price = 70000 + random.uniform(-500, 500)
        return {
            "tr_cd": "H0STCNT0",
            "tr_key": symbol,
            "rt_cd": "0",
            "data": {
                "stck_cntg_hour": datetime.now().strftime("%H%M%S"),
                "stck_prpr": round(price, 0),
                "prdy_vrss": round(price - 70000, 0),
                "prdy_ctrt": round((price - 70000) / 70000 * 100, 2),
                "acml_vol": random.randint(1000000, 20000000),
                "cntg_vol": random.randint(10, 5000)
            }
        }

    @staticmethod
    def generate_kiwoom_tick(symbol: str) -> Dict[str, Any]:
        """키움 RE 실시간 체결 데이터 (FID) 모킹"""
        price = 70000 + random.uniform(-500, 500)
        return {
            "symbol": symbol,
            "10": str(round(price, 0)), # 현재가
            "11": str(round(price - 70000, 0)), # 전일대비
            "15": str(random.randint(1000000, 20000000)), # 거래량
            "20": datetime.now().strftime("%H%M%S") # 시간
        }

async def mock_stream_producer(queue: asyncio.Queue, broker: str, symbols: List[str]):
    """
    모킹 데이터를 큐에 지속적으로 공급하는 제너레이터
    """
    provider = MockDataProvider()
    logger.info(f"🎭 Mock Stream Producer Started for {broker}")
    
    while True:
        for symbol in symbols:
            if broker == "mirae":
                data = provider.generate_mirae_tick(symbol)
            elif broker == "kiwoom_re":
                data = provider.generate_kiwoom_tick(symbol)
            else:
                data = {"error": "unknown broker"}
            
            await queue.put(data)
            await asyncio.sleep(random.uniform(0.1, 0.5)) # 랜덤 지연
