import asyncio
import logging
import json
from typing import Dict, Set, Optional
import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("StreamManager")

class StreamManager:
    """
    WebSocket Connection & Redis Pub/Sub Manager (Singleton)
    - Redis 'orderbook.kiwoom.*' 채널 데이터를 구독하여
    - 연결된 WebSocket 클라이언트에게 브로드캐스트합니다.
    """
    _instance = None
    
    def __new__(cls, redis_url: str):
        if cls._instance is None:
            cls._instance = super(StreamManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, redis_url: str):
        if self._initialized:
            return
            
        self.redis_url = redis_url
        self.active_connections: Dict[str, Set[WebSocket]] = {} # symbol -> sockets
        self._listener_task: Optional[asyncio.Task] = None
        self._initialized = True

    async def connect(self, websocket: WebSocket, symbol: str):
        """클라이언트 연결 수락"""
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
        self.active_connections[symbol].add(websocket)
        logger.info(f"WS Connected: {symbol} (Total: {len(self.active_connections[symbol])})")

    def disconnect(self, websocket: WebSocket, symbol: str):
        """클라이언트 연결 해제"""
        if symbol in self.active_connections:
            self.active_connections[symbol].discard(websocket)
            if not self.active_connections[symbol]:
                del self.active_connections[symbol]
        logger.info(f"WS Disconnected: {symbol}")

    async def start_listening(self):
        """
        Redis Pub/Sub 구독 시작 (Background Task)
        Pattern: orderbook.kiwoom.*
        """
        try:
           # direct redis connection for psubscribe (broadcaster lib supports simple sub, but we need pattern)
           self.redis = await redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
           pubsub = self.redis.pubsub()
           await pubsub.psubscribe("orderbook.kiwoom.*")
           logger.info("StreamManager: Listening to orderbook.kiwoom.*")
           
           async for message in pubsub.listen():
               if message['type'] == 'pmessage':
                    await self._handle_message(message)
                    
        except asyncio.CancelledError:
            logger.info("StreamManager: Listener Cancelled")
        except Exception as e:
            logger.error(f"StreamManager Error: {e}")
            await asyncio.sleep(5)
            # Retry logic could be added here

    async def _handle_message(self, message):
        """Redis 메시지를 WebSocket으로 전달"""
        channel = message['channel']
        data = message['data'] # JSON string
        
        # Extract symbol from channel: orderbook.kiwoom.{symbol}
        try:
            parts = channel.split('.')
            if len(parts) < 3:
                return
            symbol = parts[2]
            
            if symbol in self.active_connections:
                # Broadcast to all connected clients for this symbol
                # Copy set to avoid size change iteration error
                targets = self.active_connections[symbol].copy()
                for ws in targets:
                    try:
                        await ws.send_text(data)
                    except Exception as e:
                        logger.warning(f"Failed to send to WS: {e}")
                        self.disconnect(ws, symbol)
                        
        except Exception as e:
            logger.error(f"Message Handle Error: {e}")
