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
logger = logging.getLogger("USCollector")

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_WS_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:21000")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs", "market_symbols.yaml")

class KISRealCollectorUS:
    """미국 시장 실시간 데이터 수집기 (HDFSCNT0)"""
    def __init__(self):
        self.redis = None
        self.approval_key = None
        self.us_symbols = []
        
    def load_config(self):
        """설정 파일로부터 수집 대상 미국 주식 종목 로드"""
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        market_config = config.get('market_data', {})
        
        # US Symbols only for this collector
        us_targets = []
        if 'us' in market_config:
            data = market_config['us']
            for category in ['indices', 'leverage']:
                for item in data.get(category, []):
                    prefix = "NYS" if item['symbol'] in ['SPY', 'DIA', 'XLK', 'XLF', 'XLV'] else "NAS"
                    us_targets.append(f"{prefix}{item['symbol']}")
            
            for sector in data.get('sectors', {}).values():
                symbol = sector['etf']['symbol']
                prefix = "NYS" if symbol in ['XLK', 'XLF', 'XLV'] else "NAS"
                us_targets.append(f"{prefix}{symbol}")

        self.us_symbols = list(set(us_targets))
        return self.us_symbols

    async def get_approval_key(self):
        """KIS 웹소켓 접속을 위한 전용 Approval Key 발급 (미국)"""
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

    def parse_us_tick(self, body_str: str):
        """US 틱 데이터 파싱 (HDFSCNT0)"""
        fields = body_str.split('^')
        try:
            # US Format: [Exch|Sym|Time|Price|Diff|...|Vol]
            # HDFSCNT0 Field 11: Price, Field 13: Vol
            return MarketData(
                symbol=fields[1], price=float(fields[11]),
                change=0.0, volume=float(fields[13]),
                timestamp=datetime.now()
            )
        except (IndexError, ValueError) as e:
            logger.error(f"US Parsing Error: {e} | Raw: {body_str}")
            return None

    async def handle_message(self, message: str):
        """웹소켓 메시지 통합 처리 및 Redis 발행 (US Only)"""
        if message[0] not in ['0', '1']:
            if '"tr_id":"PINGPONG"' in message:
                return "PONG"
            logger.debug(f"Ignored (not 0/1): {message[:50]}")
            return None

        parts = message.split('|')
        if len(parts) < 4:
            logger.warning(f"Parts < 4: {len(parts)} | {message[:100]}")
            return None

        tr_id = parts[1]
        body = parts[3]
        
        ticker = None
        if tr_id == "HDFSCNT0":
            ticker = self.parse_us_tick(body)
        else:
            logger.debug(f"Unknown tr_id: {tr_id}")

        if ticker:
            await self.redis.publish("market_ticker", ticker.model_dump_json())
            logger.debug(f"✅ Published: {ticker.symbol} @ {ticker.price}")
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

                    logger.info(f"[{tr_id}] Waiting for messages...")
                    msg_count = 0
                    async for message in websocket:
                        msg_count += 1
                        if msg_count % 10 == 1:  # Log every 10th message
                            logger.info(f"[{tr_id}] Received message #{msg_count}: {message[:100]}...")
                        res = await self.handle_message(message)
                        if res == "PONG":
                            await websocket.send(message)
            except Exception as e:
                logger.error(f"[{tr_id}] WS Error: {e}")
                await asyncio.sleep(5)

    async def schedule_key_refresh(self):
        """매일 오후 10시(22:00)에 키를 초기화하여 미국장 시작 전 갱신을 유도한다."""
        while True:
            now = datetime.now()
            target = now.replace(hour=22, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            logger.info(f"[US] Next key refresh scheduled at {target} (in {wait_seconds:.0f}s)")
            
            await asyncio.sleep(wait_seconds)
            
            logger.info("🚨 [US] Scheduled key refresh (22:00 PM). Resetting approval key.")
            self.approval_key = None
            # Alert publish
            if self.redis:
                alert_msg = {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": "US Market API Key Reset (Scheduled at 22:00 PM)"
                }
                await self.redis.publish("system_alerts", json.dumps(alert_msg))

    async def run(self):
        self.redis = await redis.from_url(REDIS_URL, decode_responses=True)
        self.load_config()
        logger.info(f"Loaded {len(self.us_symbols)} US symbols for independent collection")
        
        await asyncio.gather(
            self._run_ws_loop("HDFSCNT0", self.us_symbols),
            self.schedule_key_refresh()
        )

if __name__ == "__main__":
    collector = KISRealCollectorUS()
    asyncio.run(collector.run())
