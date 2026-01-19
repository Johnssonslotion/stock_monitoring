import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
import aiohttp
import websockets

from src.data_ingestion.price.schemas.kiwoom_re import KiwoomTickData
from src.core.config import get_redis_connection
from src.data_ingestion.logger.raw_logger import RawWebSocketLogger

logger = logging.getLogger(__name__)


# Explicit Core ETF List (Leverage/Inverse mainly)
CORE_ETFS = {
    "122630", # KODEX 레버리지
    "252670", # KODEX 200선물인버스2X
    "114800", # KODEX 인버스
    "069500", # KODEX 200
}

class KiwoomWSCollector:
    """
    Kiwoom Open API+ WebSocket Collector (Hybrid: Core + Satellite)
    
    특징:
    - WebSocket URL: wss://api.kiwoom.com:10000/api/dostk/websocket
    - Core Coverage: Major Stocks + ETFs (Pre-loaded)
    - Satellite Coverage: Dynamic Subscription via Scanner
    - Screen Number Logic: 0000-0199 (Max 200 screens * 100 symbols)
    """
    
    WS_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    REST_URL = "https://api.kiwoom.com/oauth2/token"  # Official API domain
    MAX_SYMBOLS_PER_SCREEN = 50  # 안전하게 50으로 설정 (Max 100)
    
    def __init__(self, app_key: str, app_secret: str, symbols: List[str], mock_mode: bool = False):
        self.app_key = app_key
        self.app_secret = app_secret
        self.target_symbols = set(symbols) | CORE_ETFS
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self.token_expire: Optional[datetime] = None
        self.running = False
        self.redis = None
        
        # Environment-based URL selection
        if mock_mode:
            self.WS_URL = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"
            self.REST_URL = "https://mockapi.kiwoom.com/oauth2/token"
        
        # Screen Number Management
        # screen_no -> set(symbols)
        self.screen_map: Dict[str, Set[str]] = {}
        self._assign_screens(list(self.target_symbols))

        # Raw Logger (Separate Directory to avoid conflict with KIS)
        self.raw_logger = RawWebSocketLogger(log_dir="data/raw/kiwoom", retention_hours=48)

    def _assign_screens(self, symbols: List[str]):
        """종목들을 화면번호에 분산 할당"""
        self.screen_map.clear()
        chunk_size = self.MAX_SYMBOLS_PER_SCREEN
        
        for i, chunk in enumerate(self._chunk_list(symbols, chunk_size)):
            screen_no = f"{i:04d}"  # 0000, 0001, ...
            self.screen_map[screen_no] = set(chunk)
            
    def _chunk_list(self, lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    async def start(self):
        """Collector 시작"""
        self.running = True
        self.redis = await get_redis_connection()
        self.session = aiohttp.ClientSession()
        await self.raw_logger.start()
        
        token_retry_count = 0
        max_token_retries = 3
        
        while self.running:
            try:
                if not self.token or self._is_token_expired():
                    # Rate limiting: 토큰 재발급 실패 시 대기 시간 증가
                    if token_retry_count > 0:
                        wait_time = min(5 * (2 ** token_retry_count), 60)
                        logger.warning(f"⏳ Token refresh retry {token_retry_count}/{max_token_retries}, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    
                    try:
                        await self._refresh_token()
                        token_retry_count = 0
                        # ALERT: Login Success
                        await self._publish_alert("INFO", "Kiwoom Token Refreshed & Ready")
                    except Exception as token_error:
                        token_retry_count += 1
                        if token_retry_count >= max_token_retries:
                            msg = f"❌ Token refresh failed {max_token_retries} times. Waiting 5 minutes..."
                            logger.error(msg)
                            await self._publish_alert("CRITICAL", msg)
                            await asyncio.sleep(300)
                            token_retry_count = 0
                        raise
                    
                await self._connect()
            except Exception as e:
                logger.error(f"Kiwoom WS Connection Failed: {e}")
                await self._publish_alert("ERROR", f"Kiwoom Connection Failed: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Collector 종료"""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

    async def _connect(self):
        """WebSocket 연결 및 구독 (websockets 라이브러리 사용)"""
        logger.info(f"Connecting to Kiwoom WS: {self.WS_URL}")
        
        async with websockets.connect(self.WS_URL) as ws:
            self.ws = ws
            logger.info("✅ Kiwoom WS Connected")
            
            # 1. LOGIN 필수 (첫 메시지)
            await self._send_login()
            login_resp = await ws.recv()
            await self._handle_message(login_resp)
            
            # 2. REG (구독)
            await self._subscribe_all()
            
            # 3. 메시지 루프
            async for msg in ws:
                await self._handle_message(msg)

    async def _send_login(self):
        """LOGIN 메시지 전송 (필수)"""
        login_msg = {
            "trnm": "LOGIN",
            "token": self.token
        }
        await self.ws.send(json.dumps(login_msg))
        logger.info("📤 SENT LOGIN")

    async def _subscribe_all(self):
        """할당된 모든 화면번호에 대해 REG 요청"""
        for screen_no, symbols in self.screen_map.items():
            if not symbols:
                continue
            
            # Kiwoom REG 포맷
            reg_msg = {
                "trnm": "REG",
                "grp_no": screen_no,
                "refresh": "1",
                "data": [{
                    "item": list(symbols),
                    "type": ["0B"]  # 주식체결
                }]
            }
            
            await self.ws.send(json.dumps(reg_msg))
            msg = f"📤 REG Screen {screen_no}: {len(symbols)} symbols"
            logger.info(msg)
            await self._publish_alert("INFO", msg)
            
            # 응답 대기
            resp = await self.ws.recv()
            await self._handle_message(resp)
            
            await asyncio.sleep(0.2)  # Rate Limit

    async def _handle_message(self, raw_data: str):
        """메시지 처리"""
        # 💾 RAW LOGGING
        if self.raw_logger:
            await self.raw_logger.log(raw_data, direction="RX")

        try:
            data = json.loads(raw_data)
            
            # LOGIN/REG 응답
            trnm = data.get("trnm")
            if trnm in ["LOGIN", "REG", "PING"]:
                logger.info(f"📥 {trnm} response: {data}")
                return
            
            # REAL 데이터 처리
            if trnm == "REAL":
                real_data_list = data.get("data", [])
                for item in real_data_list:
                    symbol = item.get("item")
                    values = item.get("values", {})
                    
                    if symbol and values:
                        # KiwoomTickData로 변환
                        tick = KiwoomTickData.from_ws_json(values, symbol)
                        await self._publish_to_redis(tick)
                
        except Exception as e:
            logger.debug(f"Msg Parse Error: {e}")

    async def _publish_to_redis(self, tick: KiwoomTickData):
        """Redis Pub/Sub 발행"""
        channel = f"tick:KR:{tick.symbol}"
        message = tick.json()
        await self.redis.publish(channel, message)

    async def _publish_alert(self, level: str, message: str):
        """Publish system alert to Redis"""
        try:
            if self.redis:
                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "Kiwoom-Service",
                    "level": level,
                    "message": message
                }
                await self.redis.publish("system:alerts", json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}")

    async def add_symbol(self, symbol: str):
        """동적 구독 추가 (Scanner 연동용)"""
        if symbol in self.target_symbols:
            return

        self.target_symbols.add(symbol)
        
        # 빈 공간이 있는 화면번호 찾기
        target_screen = None
        for screen_no, symbols in self.screen_map.items():
            if len(symbols) < self.MAX_SYMBOLS_PER_SCREEN:
                target_screen = screen_no
                break
        
        if not target_screen:
            # 새 화면번호 할당
            new_idx = len(self.screen_map)
            target_screen = f"{new_idx:04d}"
            self.screen_map[target_screen] = set()

        self.screen_map[target_screen].add(symbol)
        
        # 추가 구독 요청 전송
        # Re-subscribe affected screen
        if self.ws and not self.ws.closed:
             await self._subscribe_screen(target_screen)

    async def _refresh_token(self):
        """Get OAuth2 Access Token from Kiwoom API"""
        # Kiwoom API Token Request Format
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        # Headers based on kiwoom_websocket_guide.md
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }
        
        try:
            async with self.session.post(self.REST_URL, json=payload, headers=headers) as resp:
                response_text = await resp.text()
                
                if resp.status == 200:
                    data = await resp.json()
                    self.token = data.get("token")
                    if self.token:
                        # Set expiration (typically 24h, but we use 20h for safety)
                        expires_in = int(data.get("expires_in", 86400))
                        from datetime import timedelta
                        self.token_expire = datetime.now() + timedelta(seconds=expires_in - 600)
                        logger.info(f"✅ Kiwoom Token Refreshed: {self.token[:10]}... (Expires at {self.token_expire})")
                else:
                    logger.error(f"❌ Token Refresh Failed: {resp.status} | Response: {response_text}")
                    raise Exception(f"Token Refresh Failed: HTTP {resp.status}")
                    
        except Exception as e:
            logger.error(f"❌ Token Refresh Error: {e}")
            raise

    async def _subscribe_screen(self, screen_no: str):
        """Single Screen Subscription"""
        symbols = self.screen_map.get(screen_no, set())
        if not symbols:
            return

        payload = {
            "header": {
                "token": self.token,
                "tr_type": "3",
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0", 
                    "tr_key": ";".join(symbols)
                }
            }
        }
        await self.ws.send(json.dumps(payload))
        logger.info(f"Subscribed Screen {screen_no}: {len(symbols)} symbols")

    def _is_token_expired(self) -> bool:
        """토큰 만료 여부 확인 (10분 여유)"""
        if not self.token or not self.token_expire:
            return True
        now = datetime.now()
        return now >= self.token_expire
