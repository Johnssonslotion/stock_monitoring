import asyncio
import os
import json
import logging
import yaml
import aiohttp
import websockets
import redis.asyncio as redis
from datetime import datetime
from src.core.schema import OrderbookData, OrderbookUnit, MessageType
from pydantic import ValidationError

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ASPCollector")

# 환경 변수 설정
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_BASE_URL = os.getenv("KIS_BASE_URL")
KIS_WS_URL = os.getenv("KIS_WS_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CONFIG_PATH = "configs/market_symbols.yaml"

# 스냅샷 샘플링 주기 (1초)
SNAPSHOT_INTERVAL = 1.0

class KISASPCollector:
    """
    한국 실시간 호가 수집기 (H0STASP0)
    제한적 수집 전략: 핵심 종목 선정 + 1초 단위 스냅샷
    """
    def __init__(self):
        self.approval_key = None
        self.symbols = []
        self.redis = None
        self.last_published = {} # 종목별 마지막 발행 시간

    def load_config(self):
        """설정 파일로부터 수집 대상 종목 필터링 및 로드"""
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 헌장(Zero-Cost)에 따라 호가 데이터는 '섹터별 top1' 또는 '인덱스' 대장주만 선정
        kr_config = config.get('market_data', {}).get('kr', {})
        targets = []
        
        # 1. 인덱스 대장주 (KODEX 200 등)
        for item in kr_config.get('indices', [])[:1]:
            targets.append(item['symbol'])
        
        # 2. 섹터별 1위 주식만 선정 (Selective Sampling)
        for sector in kr_config.get('sectors', {}).values():
            if sector.get('top3'):
                targets.append(sector['top3'][0]['symbol'])
        
        self.symbols = list(set(targets))
        logger.info(f"Target Leader Symbols for Orderbook: {self.symbols}")
        return self.symbols

    async def get_approval_key(self):
        """KIS 웹소켓 접속을 위한 Approval Key 발급"""
        url = f"{KIS_BASE_URL}/oauth2/Approval"
        headers = {"content-type": "application/json; utf-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": KIS_APP_KEY,
            "secretkey": KIS_APP_SECRET
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
                data = await resp.json()
                self.approval_key = data.get("approval_key")
                return self.approval_key

    def parse_orderbook(self, body_str: str):
        """
        H0STASP0 데이터 패킷 파싱 (상위 5단계 호가 추출)
        """
        fields = body_str.split('^')
        try:
            symbol = fields[0]
            asks = []
            bids = []
            
            # KIS 가이드 기반 인덱스 매핑 (매도호가1: 3, 매수호가1: 13, 잔량 등)
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
                bids=bids,
                timestamp=datetime.now()
            )
        except (IndexError, ValueError, ValidationError) as e:
            logger.error(f"Parse Error: {e}")
            return None

    async def run_ws(self):
        """웹소켓 연결 및 데이터 수집 루프"""
        await self.get_approval_key()
        self.redis = await redis.from_url(REDIS_URL, decode_responses=True)
        
        async with websockets.connect(KIS_WS_URL) as ws:
            # 구독 메시지 전송
            for symbol in self.symbols:
                approval_msg = {
                    "header": {
                        "approval_key": self.approval_key,
                        "custtype": "P",
                        "tr_type": "1",
                        "content-type": "utf-8"
                    },
                    "body": {
                        "input": {
                            "tr_id": "H0STASP0",
                            "tr_key": symbol
                        }
                    }
                }
                await ws.send(json.dumps(approval_msg))
                logger.info(f"Subscribed KR Orderbook: {symbol}")

            while True:
                msg = await ws.recv()
                if msg.startswith('0') or msg.startswith('1'):
                    parts = msg.split('|')
                    if len(parts) > 3:
                        body = parts[3]
                        parsed = self.parse_orderbook(body)
                        if parsed:
                            symbol = parsed.symbol
                            now = datetime.now().timestamp()
                            
                            # 1초 샘플링 (Throttling)
                            last_ts = self.last_published.get(symbol, 0)
                            if now - last_ts >= SNAPSHOT_INTERVAL:
                                await self.redis.publish("market_orderbook", parsed.model_dump_json())
                                self.last_published[symbol] = now
                else:
                    logger.debug(f"WS Message: {msg}")

    async def run(self):
        """수집기 실행 및 예외 발생 시 재연결"""
        self.load_config()
        while True:
            try:
                await self.run_ws()
            except Exception as e:
                logger.error(f"WS Exception: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    collector = KISASPCollector()
    asyncio.run(collector.run())
