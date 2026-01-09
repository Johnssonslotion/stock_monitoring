import asyncio
import logging
import os
import json
import yaml
import aiohttp
import redis.asyncio as redis
from datetime import datetime, timedelta
from src.core.schema import MarketData, MessageType

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KRCollector")

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_WS_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:21000")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs", "market_symbols.yaml")

class KISRealCollectorKR:
    """한국 시장 실시간 데이터 수집기 (H0STCNT0)"""
    def __init__(self):
        self.redis = None
        self.approval_key = None
        self.kr_symbols = []
        
    def load_config(self):
        """설정 파일로부터 수집 대상 한국 주식 종목 로드"""
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        market_config = config.get('market_data', {})
        
        # 1. KR Symbols
        kr_targets = []
        if 'kr' in market_config:
            data = market_config['kr']
            for item in data.get('indices', []) + data.get('leverage', []):
                kr_targets.append(item['symbol'])
            for sector in data.get('sectors', {}).values():
                kr_targets.append(sector['etf']['symbol'])
                for stock in sector['top3']:
                    kr_targets.append(stock['symbol'])
        self.kr_symbols = list(set(kr_targets))
        return self.kr_symbols

    async def get_approval_key(self):
        """KIS 웹소켓 접속을 위한 전용 Approval Key 발급"""
        url = f"{KIS_BASE_URL}/oauth2/Approval"
        headers = {"content-type": "application/json; utf-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": APP_KEY,
            "secretkey": APP_SECRET
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
                data = await resp.json()
                if "approval_key" in data:
                    return data["approval_key"]
                else:
                    logger.error(f"Failed to get approval key: {data}")
                    raise Exception("Auth Failed")

    def parse_kr_tick(self, body_str: str):
        """KR 틱 데이터 파싱 (H0STCNT0)"""
        fields = body_str.split('^')
        try:
            return MarketData(
                symbol=fields[0], price=float(fields[2]),
                change=float(fields[5]), volume=float(fields[12]),
                timestamp=datetime.now()
            )
        except (IndexError, ValueError) as e:
            logger.error(f"KR Parsing Error: {e} | Raw: {body_str}")
            return None

    async def handle_message(self, message: str):
        """웹소켓 메시지 통합 처리 및 Redis 발행 (KR Only)"""
        if message[0] not in ['0', '1']:
            if '"tr_id":"PINGPONG"' in message:
                return "PONG"
            return None

        parts = message.split('|')
        if len(parts) < 4:
            return None

        tr_id = parts[1]
        body = parts[3]
        
        ticker = None
        if tr_id == "H0STCNT0":
            ticker = self.parse_kr_tick(body)

        if ticker:
            await self.redis.publish("market_ticker", ticker.model_dump_json())
        return tr_id

    async def _run_ws_loop(self, tr_id: str, symbols: list):
        """범용 웹소켓 연결 및 수집 루프"""
        import websockets
        if not symbols:
            logger.info(f"[{tr_id}] No symbols to subscribe. Skipping.")
            return

        while True:
            try:
                if not self.approval_key:
                    logger.info(f"[{tr_id}] Approval key is missing. Fetching...")
                    self.approval_key = await self.get_approval_key()

                ws_url = f"{KIS_WS_URL}/{tr_id}"
                logger.info(f"[{tr_id}] Connecting to {ws_url}...")
                
                async with websockets.connect(ws_url) as websocket:
                    logger.info(f"[{tr_id}] Connected. Subscribing {len(symbols)} symbols.")
                    for sym in symbols:
                        req = {
                            "header": {"approval_key": self.approval_key, "custtype": "P", "tr_type": "1", "content-type": "utf-8"},
                            "body": {"input": {"tr_id": tr_id, "tr_key": sym}}
                        }
                        await websocket.send(json.dumps(req))
                        await asyncio.sleep(0.1)

                    async for message in websocket:
                        res = await self.handle_message(message)
                        if res == "PONG":
                            await websocket.send(message)
            except Exception as e:
                logger.error(f"[{tr_id}] WS Error: {e}")
                await asyncio.sleep(5)

    async def schedule_key_refresh(self):
        """매일 오전 8시(08:00)에 키를 초기화하여 한국장 시작 전 갱신을 유도한다."""
        while True:
            now = datetime.now()
            target = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            logger.info(f"[KR] Next key refresh scheduled at {target} (in {wait_seconds:.0f}s)")
            
            await asyncio.sleep(wait_seconds)
            
            logger.info("🚨 [KR] Scheduled key refresh (08:00 AM). Resetting approval key.")
            self.approval_key = None
            # Alert publish
            if self.redis:
                alert_msg = {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": "KR Market API Key Reset (Scheduled at 08:00 AM)"
                }
                await self.redis.publish("system_alerts", json.dumps(alert_msg))

    async def run(self):
        self.redis = await redis.from_url(REDIS_URL, decode_responses=True)
        self.load_config()
        logger.info(f"Loaded {len(self.kr_symbols)} KR symbols for independent collection")
        
        await asyncio.gather(
            self._run_ws_loop("H0STCNT0", self.kr_symbols),
            self.schedule_key_refresh()
        )

if __name__ == "__main__":
    collector = KISRealCollectorKR()
    asyncio.run(collector.run())
