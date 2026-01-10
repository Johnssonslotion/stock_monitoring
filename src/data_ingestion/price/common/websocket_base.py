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
        self.raw_logger = RawWebSocketLogger(retention_hours=24)
        
        # Dynamic URL State
        self.current_ws_url: Optional[str] = None
        
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
                     logger.warning(f"[API MSG] {data['body']['msg1']}")
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
                logger.info(f"📤 PUBLISHED: {channel} | {data_obj.symbol} @ {data_obj.price}")
            elif not data_obj:
                logger.warning(f"⚠️  PARSE FAILED: tr_id={tr_id}")
        else:
            logger.warning(f"❌ UNKNOWN tr_id: {tr_id}")
        
        return tr_id

    async def _send_request(self, tr_id: str, tr_key: str, tr_type: str):
        """내부 요청 전송 헬퍼"""
        async with self.ws_lock:
            if not self.websocket or not self.approval_key:
                logger.warning("WebSocket not connected or no key")
                return
            
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
                    await self._send_request(tr_id, sym, "1") # 1=Subscribe
                    await asyncio.sleep(0.2) # Rate Limit
                    count += 1
        
        self.active_markets.add(market)
        logger.info(f"[{market}] Subscribed {count} symbols.")

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
                    await self._send_request(tr_id, sym, "2") # 2=Unsubscribe
                    await asyncio.sleep(0.2)
                    count += 1
        
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

    async def run(self, ws_url: str, approval_key: str):
        """메인 실행 루프"""
        import websockets
        
        self.approval_key = approval_key
        await self.connect_redis()
        
        # Load Symbols Initially (without subscribing)
        for c in self.collectors.values():
            c.load_symbols()
            logger.info(f"[{c.market}] Loaded {len(c.symbols)} symbols")

        # Set initial URL
        self.current_ws_url = ws_url

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
                    
                    # Note: 구독은 외부 스케줄러(schedule_market_switch)가 수행함.
                    # 하지만 최초 연결 시 빠른 복구를 위해 스케줄러가 '즉시' 깨어나야 함.
                    # 여기서는 그냥 대기.
                    
                    # 메시지 루프
                    async for message in websocket:
                        res = await self.handle_message(message)
                        if res == "PONG":
                            await websocket.send(message)
                            
            except Exception as e:
                logger.error(f"WS Connection Error: {e}")
                async with self.ws_lock:
                    self.websocket = None
                    self.active_markets.clear()
                await asyncio.sleep(5)
