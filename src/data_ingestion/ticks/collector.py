import asyncio
import json
import logging
import aiohttp
import redis.asyncio as redis
from typing import Optional, Dict, Any
from src.core.config import settings

logger = logging.getLogger(__name__)

class TickCollector:
    """
    틱 데이터 수집기 (Tick Collector)
    
    웹소켓을 통해 거래소(Upbit 등)에서 실시간 체결(Tick) 데이터를 수신하고,
    정규화(Normalize)하여 Redis Pub/Sub 채널로 발행합니다.
    
    Attributes:
        exchange_name (str): 거래소 이름 (예: 'upbit')
        symbols (list): 수집 대상 심볼 리스트 (예: ['KRW-BTC'])
        redis_url (str): Redis 접속 URL
    """
    
    def __init__(self):
        self.exchange_name = settings.exchange.name
        self.symbols = settings.exchange.symbols
        self.redis_url = settings.data.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        
        # Upbit WebSocket Endpoint
        self.ws_url = "wss://api.upbit.com/websocket/v1"

    async def connect_redis(self):
        """Redis 연결을 초기화합니다."""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis")

    async def publish_tick(self, tick_data: Dict[str, Any]):
        """
        정규화된 틱 데이터를 Redis 채널로 발행합니다.
        
        Channel Format: tick.{exchange}.{symbol}
        """
        if not self.redis_client:
            return
            
        symbol = tick_data.get("symbol")
        channel = f"tick.{self.exchange_name}.{symbol}"
        
        # Fire and forget (Pub/Sub)
        await self.redis_client.publish(channel, json.dumps(tick_data))
        # logger.debug(f"Published to {channel}: {tick_data}")

    def normalize(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        거래소별 원본 데이터를 표준 포맷으로 변환합니다.
        
        Args:
            raw_data (dict): 거래소 수신 원본 데이터
            
        Returns:
            dict: 표준화된 틱 데이터 (유효하지 않으면 None)
        """
        try:
            # Upbit Format Check
            if "code" not in raw_data or "trade_price" not in raw_data:
                return None
                
            return {
                "source": self.exchange_name,
                "symbol": raw_data["code"],
                "timestamp": raw_data["trade_timestamp"], # Milliseconds since epoch? Upbit provides trade_timestamp in ms? No, need check.
                # Upbit: trade_timestamp (Long) 체결 타임스탬프 (milliseconds)
                "price": float(raw_data["trade_price"]),
                "volume": float(raw_data["trade_volume"]),
                "side": "ask" if raw_data["ask_bid"] == "ASK" else "bid", # ASK:매도, BID:매수
                "id": f"{raw_data['trade_date']}-{raw_data['trade_time']}-{raw_data['sequential_id']}"
            }
        except Exception as e:
            logger.error(f"Normalization error: {e}, Data: {raw_data}")
            return None

    async def run(self):
        """수집기 메인 루프 (Asyncio Event Loop 진입점)"""
        self.running = True
        await self.connect_redis()
        
        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.ws_url) as ws:
                        logger.info(f"Connected to Upbit WebSocket: {self.ws_url}")
                        
                        # Subscribe Request
                        codes = self.symbols
                        subscribe_data = [
                            {"ticket": "antigravity-uuid"},
                            {"type": "trade", "codes": codes}
                        ]
                        await ws.send_json(subscribe_data)
                        
                        async for msg in ws:
                            if not self.running:
                                break
                                
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                # Upbit sends Blob (Binary) usually, but aiohttp handles text
                                # Check if Upbit sends binary
                                pass
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                data = json.loads(msg.data)
                                normalized = self.normalize(data)
                                if normalized:
                                    await self.publish_tick(normalized)
                                    
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket Error: {msg.data}")
                                break
            except Exception as e:
                logger.error(f"Connection lost: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    # 간단한 실행 테스트 (Production에서는 별도 Entrypoint 사용)
    logging.basicConfig(level=logging.INFO)
    collector = TickCollector()
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        pass
