"""
KIS WebSocket 통합 수집 및 관리 모듈
"""
import asyncio
import logging
import json
import redis.asyncio as redis
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from src.core.schema import MarketData
from src.data_ingestion.logger.raw_logger import RawWebSocketLogger

logger = logging.getLogger(__name__)

class BaseCollector(ABC):
    """
    시장별 수집기 인터페이스 (로직 정의용)
    - 실행 루프를 가지지 않고, 파싱 로직과 심볼 로딩만 담당
    """
    def __init__(self, market: str, tr_id: str):
        self.market = market
        self.tr_id = tr_id
        self.symbols = []

    @abstractmethod
    def parse_tick(self, body_str: str) -> Optional[MarketData]:
         pass
    
    @abstractmethod
    def load_symbols(self) -> list:
        pass
        
    @abstractmethod
    def get_channel(self) -> str:
        """Redis 채널명 반환 (예: ticker.kr, orderbook.us)"""
        pass


class UnifiedWebSocketManager:
    """
    통합 WebSocket 연결 관리자
    - 단일 WebSocket 연결 유지
    - 동적 구독/해제 (Subscribe/Unsubscribe) 지원
    - Raw Logging 지원
    """
    def __init__(self, collectors: List[BaseCollector], redis_url: str):
        self.collectors: Dict[str, BaseCollector] = {c.tr_id: c for c in collectors}
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        
        # WebSocket State
        self.websocket = None
        self.ws_lock = asyncio.Lock()
        self.approval_key = None
        
        # Subscription State (to prevent redundant requests)
        self.active_markets = set()
        
        # Raw Logger
        self.raw_logger = RawWebSocketLogger(retention_hours=120)  # 5일 보존
        
        # Dynamic URL State
        self.current_ws_url: Optional[str] = None
        
        # Auto-Refresh Callback
        self.key_refresh_callback = None
        self.last_refresh_time = 0
        
    def set_refresh_callback(self, callback):
        """Set callback for auto key refresh"""
        self.key_refresh_callback = callback
        
    async def connect_redis(self):
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        logger.info("✅ Redis Connected")
        await self.raw_logger.start()

    async def handle_message(self, message: str) -> Optional[str]:
        # 💾 RAW LOGGING
        await self.raw_logger.log(message, direction="RX")

        # 🔍 DEBUG: Log ALL messages (first 200 chars)
        logger.debug(f"📨 RAW MSG: {message[:200]}")
        
        # PINGPONG 처리
        if message[0] not in ['0', '1']:
            logger.debug(f"⏭️  SKIP: First char not 0/1 -> {message[0]}")
            if '"tr_id":"PINGPONG"' in message:
                return "PONG"
            
            # JSON 메시지 로깅 (에러 확인용)
            try:
                data = json.loads(message)
                if 'body' in data and 'msg1' in data['body']:
                     msg1 = data['body']['msg1']
                     logger.warning(f"[API MSG] {msg1}")
                     
                     # 🚨 KEY EXPIRED DETECTION
                     if "invalid tr_key" in msg1 or "Expired" in msg1:
                         logger.error("🚨 DETECTED INVALID KEY! Triggering Auto-Refresh...")
                         asyncio.create_task(self.trigger_refresh())
                         
            except:
                pass
            return None
        
        # 메시지 파싱
        parts = message.split('|')
        logger.debug(f"🔢 PARTS: {len(parts)} parts, tr_id candidate: {parts[1] if len(parts) > 1 else 'N/A'}")
        
        if len(parts) < 4:
            logger.warning(f"⚠️  INVALID: Only {len(parts)} parts (need 4+)")
            return None
        
        tr_id = parts[1]
        body = parts[3]
        
        # 라우팅
        collector = self.collectors.get(tr_id)
        if collector:
            logger.debug(f"✅ MATCH: tr_id={tr_id}, parsing...")
            # 파싱 위임
            data_obj = collector.parse_tick(body)
            if data_obj and self.redis:
                # Redis 발행 (동적 채널)
                channel = collector.get_channel()
                await self.redis.publish(channel, data_obj.model_dump_json())
                price = getattr(data_obj, 'price', None)
                if price is not None:
                    logger.info(f"📤 PUBLISHED: {channel} | {data_obj.symbol} @ {price}")
                else:
                    logger.info(f"📤 PUBLISHED: {channel} | {data_obj.symbol} (Type: {data_obj.type})")
            elif not data_obj:
                logger.warning(f"⚠️  PARSE FAILED: tr_id={tr_id}")
        else:
            logger.warning(f"❌ UNKNOWN tr_id: {tr_id}")
        
        return tr_id

    async def trigger_refresh(self):
        """Trigger key refresh with cooldown"""
        import time
        now = time.time()
        if now - self.last_refresh_time < 60: # 60s Cooldown
            logger.warning("⏳ Key refresh cooldown active. Skipping.")
            return

        if self.key_refresh_callback:
            self.last_refresh_time = now
            logger.info("♻️  Executing Key Refresh Callback...")
            await self.key_refresh_callback()
        else:
            logger.error("❌ No key_refresh_callback set!")

    async def _send_request(self, tr_id: str, tr_key: str, tr_type: str):
        """내부 요청 전송 헬퍼"""
        async with self.ws_lock:
            if not self.websocket or not self.approval_key:
                logger.warning("WebSocket not connected or no key")
                return False
            
            req = {
                "header": {
                    "approval_key": self.approval_key,
                    "custtype": "P",
                    "tr_type": tr_type,
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": tr_key
                    }
                }
            }
            await self.websocket.send(json.dumps(req))
            return True
    
    async def subscribe_market(self, market: str):
        """특정 시장(KR/US)의 모든 Collectors 구독"""
        if market in self.active_markets:
            logger.info(f"[{market}] Already subscribed. Skipping.")
            return

        logger.info(f"[{market}] Starting SUBSCRIPTION...")
        count = 0
        for tr_id, collector in self.collectors.items():
            if collector.market == market:
                # 심볼 로드가 안되어 있으면 로드
                if not collector.symbols:
                    collector.load_symbols()
                
                for sym in collector.symbols:
                    if await self._send_request(tr_id, sym, "1"): # 1=Subscribe
                        count += 1
                    await asyncio.sleep(0.2) # Rate Limit
        
        if count > 0:
            self.active_markets.add(market)
            logger.info(f"[{market}] Subscribed {count} symbols.")
        else:
            logger.warning(f"[{market}] Subscription FAILED (No packets sent). Will retry.")

    async def unsubscribe_market(self, market: str):
        """특정 시장(KR/US)의 모든 Collectors 구독 해제"""
        if market not in self.active_markets:
            logger.info(f"[{market}] Not subscribed. Skipping Unsubscribe.")
            return

        logger.info(f"[{market}] Starting UNSUBSCRIBE...")
        count = 0
        for tr_id, collector in self.collectors.items():
            if collector.market == market:
                for sym in collector.symbols:
                    if await self._send_request(tr_id, sym, "2"): # 2=Unsubscribe
                        count += 1
                    await asyncio.sleep(0.2)
        
        self.active_markets.discard(market)
        logger.info(f"[{market}] Unsubscribed {count} symbols.")

    async def update_key(self, new_key: str):
        """Approval Key 동적 업데이트 (Thread-safe)"""
        async with self.ws_lock:
            self.approval_key = new_key
            self.approval_key = new_key
            logger.info("🔐 Approval Key updated dynamically.")

    async def switch_url(self, new_url: str):
        """WebSocket URL 동적 변경 및 재연결 요청"""
        logger.info(f"🔄 Switching WebSocket URL to: {new_url}")
        self.current_ws_url = new_url
        
        # 현재 연결 강제 종료 -> run() 루프에서 재연결 유도
        async with self.ws_lock:
            if self.websocket:
                logger.info("🔌 Disconnecting current socket to force reconnect...")
                await self.websocket.close()
                self.websocket = None
                self.active_markets.clear()

    async def _watchdog_loop(self):
        """🐶 Traffic Watchdog: Monitors data flow and triggers recovery"""
        import time
        logger.info("🐶 Watchdog started.")
        self.last_traffic_time = time.time()
        
        while True:
            try:
                await asyncio.sleep(10)
                
                # Pre-checks
                if not self.websocket or not self.active_markets:
                    self.last_traffic_time = time.time() # Reset timer if not active
                    continue
                    
                elapsed = time.time() - self.last_traffic_time
                
                # Level 1: Warning (60s)
                if 60 <= elapsed < 120:
                     # Log only once per minute roughly
                    if int(elapsed) % 60 < 10: 
                        logger.warning(f"🐶 [Watchdog] No traffic for {int(elapsed)}s! (Active Markets: {self.active_markets})")

                # Level 2: Resubscribe (120s)
                elif 120 <= elapsed < 180:
                    logger.warning(f"🐶 [Watchdog] traffic dead for {int(elapsed)}s -> ♻️ Triggering RESUBSCRIBE")
                    # Update traffic time to prevent spamming resubscribe immediately, but keep it high enough to hit Level 3 if it fails
                    # actually, we should just let it run. But we need to be careful not to spam.
                    # Let's try resubscribing all active markets
                    current_subs = list(self.active_markets)
                    self.active_markets.clear() # Clear state to force subscribe logic to run
                    for market in current_subs:
                        await self.subscribe_market(market)
                    
                    # Give it some grace period? No, simply resetting traffic time slightly effectively gives grace
                    # But if we reset, we might miss Level 3. 
                    # Instead, we rely on the fact that if data comes in, traffic_time updates.
                    # If not, execution continues and will eventually hit 180s.
                    await asyncio.sleep(10) # Wait a bit before checking again

                # Level 3: Hard Reconnect (180s)
                elif elapsed >= 180:
                    logger.error(f"🐶 [Watchdog] traffic dead for {int(elapsed)}s -> 🔌 KILLING SOCKET")
                    if self.websocket:
                        await self.websocket.close()
                    # Resetting traffic time here isn't strictly necessary as loop will restart/socket is gone
                    self.last_traffic_time = time.time()
                    await asyncio.sleep(5) 
                    
            except asyncio.CancelledError:
                logger.info("🐶 Watchdog stopped.")
                break
            except Exception as e:
                logger.error(f"🐶 Watchdog Error: {e}")
                await asyncio.sleep(10)

    async def run(self, ws_url: str, approval_key: str):
        """메인 실행 루프"""
        import websockets
        import time
        
        self.approval_key = approval_key
        await self.connect_redis()
        
        # Load Symbols Initially (without subscribing)
        for c in self.collectors.values():
            c.load_symbols()
            logger.info(f"[{c.market}] Loaded {len(c.symbols)} symbols")

        # Set initial URL
        self.current_ws_url = ws_url
        
        # Start Watchdog
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

        try:
            while True:
                try:
                    # Use current dynamic URL
                    target_url = self.current_ws_url
                    logger.info(f"Connecting to {target_url}...")
                    
                    async with websockets.connect(
                        target_url,
                        ping_interval=20, 
                        ping_timeout=10, 
                        close_timeout=10
                    ) as websocket:
                        logger.info("Connected.")
                        
                        async with self.ws_lock:
                            self.websocket = websocket
                            self.active_markets.clear() # Reset state on reconnect
                            self.last_traffic_time = time.time() # Reset watchdog timer
                        
                        # Note: 구독은 외부 스케줄러(schedule_market_switch)가 수행함.
                        
                        # 메시지 루프
                        async for message in websocket:
                            res = await self.handle_message(message)
                            
                            # Watchdog Feed: Only feed on valid data or PONG? 
                            # PINGPONG keeps connection alive, but we want DATA.
                            # So we update only if 'res' is tr_id (data) OR 'PONG' (connection)
                            # WAIT, our goal is "Data Flow". If only PingPong, it's a zombie.
                            # So we should ONLY update on Data (tr_id).
                            # handle_message returns: "PONG", tr_id (data), or None (error/skip)
                            
                            if res and res != "PONG":
                                self.last_traffic_time = time.time()
                            
                            if res == "PONG":
                                await websocket.send(message)
                                # NOTE: We do NOT update last_traffic_time on PONG. 
                                # This enforces actual data reception.
                                
                except Exception as e:
                    logger.error(f"WS Connection Error: {e}")
                    async with self.ws_lock:
                        self.websocket = None
                        self.active_markets.clear()
                    await asyncio.sleep(5)
        finally:
            if self._watchdog_task:
                self._watchdog_task.cancel()

