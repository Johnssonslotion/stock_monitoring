from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from src.api.services.stream_manager import StreamManager
import os

router = APIRouter()

# Redis URL from Env
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
manager = StreamManager(REDIS_URL)

@router.on_event("startup")
async def startup_event():
    import asyncio
    # Start background listener
    asyncio.create_task(manager.start_listening())

@router.websocket("/ws/orderbook/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    """
    실시간 10단계 호가 스트리밍 엔드포인트
    Endpoint: /ws/orderbook/{symbol}
    """
    await manager.connect(websocket, symbol)
    try:
        while True:
            # Keep connection alive, maybe receive ping/pong or client commands
            # For now, just wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol)
    except Exception as e:
        manager.disconnect(websocket, symbol)
