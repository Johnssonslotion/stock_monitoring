from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import asyncio
import json
import os
import logging
import asyncpg
from datetime import datetime
from typing import List, Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Antigravity API", version="1.0.0")

# CORS 설정 (로컬 개발 및 Electron 앱 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수 및 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")
API_AUTH_SECRET = os.getenv("API_AUTH_SECRET", "super-secret-key")

class ConnectionManager:
    """웹소켓 연결 관리 클래스"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Broadcast Error: {e}")
                self.disconnect(connection)

manager = ConnectionManager()
db_pool: Optional[asyncpg.Pool] = None

async def verify_api_key(x_api_key: str = Header(..., alias="x-api-key")):
    """API-Key 기반 보안 인증 미들웨어"""
    if x_api_key != API_AUTH_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

@app.on_event("startup")
async def startup_event():
    global db_pool
    logger.info("🚀 Starting API server...")
    # Redis 구독 타스크 시작
    asyncio.create_task(redis_subscriber())
    # DB 커넥션 풀 초기화
    try:
        logger.info(f"📊 Connecting to DB: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        logger.info("✅ Database Pool initialized successfully!")
    except Exception as e:
        logger.error(f"❌ DB Pool Init Failed: {e}")

async def redis_subscriber():
    """Redis Pub/Sub 메시지를 브로드캐스트하는 타스크"""
    try:
        r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("market_ticker", "market_orderbook", "news_alert", "system_alerts")
        logger.info("Connected to Redis Pub/Sub.")

        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.broadcast(message["data"])
    except Exception as e:
        logger.error(f"Redis Subscriber Exception: {e}")

# --- REST API Endpoints ---

@app.get("/api/v1/ticks/{symbol}", dependencies=[Depends(verify_api_key)])
async def get_recent_ticks(symbol: str, limit: int = 100):
    """최근 틱(체결) 데이터 조회"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT time, symbol, price, volume, change 
            FROM market_ticks 
            WHERE symbol = $1 
            ORDER BY time DESC 
            LIMIT $2
        """, symbol, limit)
        
        return [dict(r) for r in rows]

@app.get("/api/v1/orderbook/{symbol}", dependencies=[Depends(verify_api_key)])
async def get_latest_orderbook(symbol: str):
    """최신 호가 스냅샷 조회"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM market_orderbook 
            WHERE symbol = $1 
            ORDER BY time DESC 
            LIMIT 1
        """, symbol)
        
        if not row:
            raise HTTPException(status_code=404, detail="Orderbook not found")
            
        data = dict(row)
        # 평탄화된 데이터를 클라이언트에 맞게 구조화 (선택 사항)
        return data

@app.get("/health")
async def health_check():
    return {"status": "ok", "db": db_pool is not None}

# --- WebSocket Endpoint ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
