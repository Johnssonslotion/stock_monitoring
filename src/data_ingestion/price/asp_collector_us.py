import asyncio
import os
import json
import logging
import yaml
import aiohttp
import websockets
import redis.asyncio as redis
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ASPCollectorUS")

# 환경 변수 설정
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_BASE_URL = os.getenv("KIS_BASE_URL")
KIS_WS_URL = os.getenv("KIS_WS_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CONFIG_PATH = "configs/market_symbols.yaml"

# 스냅샷 샘플링 주기 (1초)
SNAPSHOT_INTERVAL = 1.0

class KISASPCollectorUS:
    """
    미국 실시간 호가 수집기 (HDFSASP0)
    제한적 수집 전략: 핵심 종목 선정 + 1초 단위 스냅샷
    """
    def __init__(self):
        self.approval_key = None
        self.symbols = []
        self.redis = None
        self.last_published = {} # 종목별 마지막 발행 시간

    def load_config(self):
        """설정 파일로부터 수집 대상 미국 주식 종목 로드"""
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        us_config = config.get('market_data', {}).get('us', {})
        targets = []
        
        # 1. 인덱스 대장주 (SPY, QQQ)
        for item in us_config.get('indices', [])[:2]:
            prefix = "NYS" if item['symbol'] == "SPY" else "NAS"
            targets.append(f"{prefix}{item['symbol']}")
        
        # 2. 레버리지 대장주 (TQQQ)
        for item in us_config.get('leverage', [])[:1]:
            targets.append(f"NAS{item['symbol']}")

        # 3. 핵심 섹터 대장주 (NVDA 등)
        for sector in us_config.get('sectors', {}).values():
            if sector.get('top3'):
                symbol = sector['top3'][0]['symbol']
                prefix = "NAS" # 기본 NAS로 지정
                targets.append(f"{prefix}{symbol}")
        
        self.symbols = list(set(targets))
        logger.info(f"Target US Leader Symbols (Orderbook): {self.symbols}")
        return self.symbols

    async def get_approval_key(self):
        """KIS 웹소켓 접속을 위한 Approval Key 발급 (미국)"""
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

    def parse_us_orderbook(self, body_str: str):
        """
        HDFSASP0 데이터 패킷 파싱 (해외 주식 실시간 호가)
        """
        fields = body_str.split('^')
        try:
            symbol = fields[1]
            data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "asks": [],
                "bids": []
            }
            # 필드 오프셋은 KIS 해외주식 가이드 참조 (2씩 증가)
            for i in range(5):
                offset = i * 4
                data["asks"].append({
                    "price": float(fields[10 + offset]),
                    "vol": float(fields[11 + offset])
                })
                data["bids"].append({
                    "price": float(fields[12 + offset]),
                    "vol": float(fields[13 + offset])
                })
            return data
        except Exception as e:
            logger.error(f"US Parse Error: {e}")
            return None

    async def run_ws(self):
        """웹소켓 연결 및 데이터 수집 루프 (미국)"""
        await self.get_approval_key()
        self.redis = await redis.from_url(REDIS_URL, decode_responses=True)
        
        async with websockets.connect(KIS_WS_URL) as ws:
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
                            "tr_id": "HDFSASP0",
                            "tr_key": symbol
                        }
                    }
                }
                await ws.send(json.dumps(approval_msg))
                logger.info(f"Subscribed US Orderbook: {symbol}")

            while True:
                msg = await ws.recv()
                if msg.startswith('0') or msg.startswith('1'):
                    parts = msg.split('|')
                    if len(parts) > 3:
                        body = parts[3]
                        parsed = self.parse_us_orderbook(body)
                        if parsed:
                            symbol = parsed['symbol']
                            now = datetime.now().timestamp()
                            last_ts = self.last_published.get(symbol, 0)
                            if now - last_ts >= SNAPSHOT_INTERVAL:
                                await self.redis.publish("market_orderbook", json.dumps(parsed))
                                self.last_published[symbol] = now
                else:
                    logger.debug(f"US WS Control Message: {msg}")

    async def run(self):
        """수집기 실행 및 예외 발생 시 재연결 (미국)"""
        self.load_config()
        while True:
            try:
                await self.run_ws()
            except Exception as e:
                logger.error(f"US Orderbook WS Exception: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    collector = KISASPCollectorUS()
    asyncio.run(collector.run())
