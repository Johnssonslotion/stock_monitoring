import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
import aiohttp

from src.data_ingestion.price.schemas.kiwoom_re import KiwoomTickData
from src.core.config import get_redis_connection


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
    REST_URL = "https://api.kiwoom.com/oauth2/token"  # For Token Refresh
    MAX_SYMBOLS_PER_SCREEN = 50  # 안전하게 50으로 설정 (Max 100)
    
    def __init__(self, app_key: str, app_secret: str, symbols: List[str]):
        self.app_key = app_key
        self.app_secret = app_secret
        self.target_symbols = set(symbols) | CORE_ETFS
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self.token_expire: Optional[datetime] = None
        self.running = False
        self.redis = None
        
        # Screen Number Management
        # screen_no -> set(symbols)
        self.screen_map: Dict[str, Set[str]] = {}
        self._assign_screens(list(self.target_symbols))

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
        
        while self.running:
            try:
                if not self.token or self._is_token_expired():
                    await self._refresh_token()
                    
                await self._connect()
            except Exception as e:
                logger.error(f"Kiwoom WS Connection Failed: {e}")
                await asyncio.sleep(5)  # Retry delay

    async def stop(self):
        """Collector 종료"""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

    async def _connect(self):
        """WebSocket 연결 및 구독"""
        logger.info(f"Connecting to Kiwoom WS: {self.WS_URL}")
        
        async with self.session.ws_connect(self.WS_URL) as ws:
            self.ws = ws
            logger.info("Kiwoom WS Connected")
            
            # 초기 구독 수행
            await self._subscribe_all()
            
            # 메시지 루프
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error("Kiwoom WS Error")
                    break

    async def _subscribe_all(self):
        """할당된 모든 화면번호에 대해 구독 요청"""
        for screen_no, symbols in self.screen_map.items():
            if not symbols:
                continue
                
            # 구독 패킷 구성 (Kiwoom Spec 참조 필요, 여기서는 일반적인 JSON 포맷 가정)
            # 실시간 포맷: {"header": {...}, "body": {"input": {...}}}
            # 주의: 실제 키움 WS 프로토콜은 문서 확인 필요. 
            # 현재는 'implementation_plan.md'의 가정을 따름.
            
            payload = {
                "header": {
                    "token": "BEARER_TOKEN_REQUIRED_HERE", # TODO: Token Logic Addition
                    "tr_type": "3", # 3: Realtime Subscribe
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0", # 주식체결
                        "tr_key": ";".join(symbols)
                    }
                }
            }
            # Note: 실제 구현시 Auth Token 발급 로직 연동 필요.
            # 지금은 구조 잡기 우선.
            
            await self.ws.send_json(payload)
            logger.info(f"Subscribed Screen {screen_no}: {len(symbols)} symbols")
            await asyncio.sleep(0.2) # Rate Limit 고려

    async def _handle_message(self, raw_data: str):
        """메시지 처리"""
        try:
            data = json.loads(raw_data)
            
            # Heartbeat or System Message check
            if "body" not in data:
                return

            # 데이터 파싱
            # 실제 응답 구조에 따라 키값 조정 필요
            body = data["body"]
            symbol = body.get("MKSC_SHRN_ISCD")
            
            if symbol:
                tick = KiwoomTickData.from_ws_json(body, symbol)
                await self._publish_to_redis(tick)
                
        except Exception as e:
            logger.debug(f"Msg Parse Error: {e}")

    async def _publish_to_redis(self, tick: KiwoomTickData):
        """Redis Pub/Sub 발행"""
        channel = f"tick:KR:{tick.symbol}"
        message = tick.json()
        await self.redis.publish(channel, message)

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
        """Get OAuth2 Access Token"""
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        headers = {"Content-Type": "application/json"}
        
        async with self.session.post(self.REST_URL, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.token = data.get("access_token") or data.get("token")
                # TODO: Parse expires_in or expires_dt
                logger.info(f"Token Refreshed: {self.token[:10]}...")
            else:
                logger.error(f"Token Refresh Failed: {resp.status}")
                raise Exception("Token Refresh Failed")

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
        await self.ws.send_json(payload)
        logger.info(f"Subscribed Screen {screen_no}: {len(symbols)} symbols")

    def _is_token_expired(self) -> bool:
        # TODO: Implement accurate expiration check
        return False
