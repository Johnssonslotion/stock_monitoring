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

@app.get("/api/v1/candles/{symbol}", dependencies=[Depends(verify_api_key)])
async def get_recent_candles(symbol: str, limit: int = 200):
    """최근 분봉(Candle) 데이터 조회"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT time, open, high, low, close, volume
            FROM market_minutes
            WHERE symbol = $1
            ORDER BY time DESC
            LIMIT $2
        """, symbol, limit)
        
        # 반환 포맷: Frontend(Plotly)에서 쓰기 편하게 리스트 형태로 변환
        # 시간순 정렬 (과거 -> 현재)로 뒤집어서 반환
        return [dict(r) for r in reversed(rows)]

@app.get("/api/v1/market-map/{market}", dependencies=[Depends(verify_api_key)])
async def get_market_map(market: str = "us"):
    """
    시장별 Treemap 데이터 조회 (시가총액, 등락률, Active 여부)
    
    Args:
        market (str): 시장 구분 ('kr' = KOSPI, 'us' = NASDAQ)
    """
    import yfinance as yf
    from datetime import datetime
    
    # 시장별 종목 리스트 정의
    if market.lower() == "kr":
        # KOSPI 시가총액 상위 30개 종목
        symbols = [
            "005930.KS",  # 삼성전자
            "000660.KS",  # SK하이닉스
            "035420.KS",  # NAVER
            "051910.KS",  # LG화학
            "005380.KS",  # 현대차
            "006400.KS",  # 삼성SDI
            "000270.KS",  # 기아
            "035720.KS",  # 카카오
            "068270.KS",  # 셀트리온
            "207940.KS",  # 삼성바이오로직스
            "105560.KS",  # KB금융
            "055550.KS",  # 신한지주
            "096770.KS",  # SK이노베이션
            "012330.KS",  # 현대모비스
            "028260.KS",  # 삼성물산
            "017670.KS",  # SK텔레콤
            "066570.KS",  # LG전자
            "033780.KS",  # KT&G
            "003670.KS",  # 포스코퓨처엠
            "009150.KS",  # 삼성전기
            "034730.KS",  # SK
            "018260.KS",  # 삼성에스디에스
            "323410.KS",  # 카카오뱅크
            "003550.KS",  # LG
            "000810.KS",  # 삼성화재
            "086790.KS",  # 하나금융지주
            "032830.KS",  # 삼성생명
            "011200.KS",  # HMM
            "010130.KS",  # 고려아연
            "051900.KS",  # LG생활건강
        ]
        currency = "KRW"
        market_cap_unit = 1e12  # 조(Trillion)
    else:
        # NASDAQ 100 대표 종목 (기본값)
        symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ASML", "COST",
            "NFLX", "AMD", "PEP", "ADBE", "CSCO", "TMUS", "CMCSA", "INTC", "QCOM", "TXN",
            "INTU", "AMGN", "HON", "AMAT", "SBUX", "ISRG", "BKNG", "GILD", "MDLZ", "VRTX"
        ]
        currency = "USD"
        market_cap_unit = 1e9  # 십억(Billion)
    
    # DB에서 Active 심볼 조회 (실시간 데이터 수집 여부)
    active_symbols = set()
    if db_pool:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT symbol FROM market_minutes")
            active_symbols = {row['symbol'] for row in rows}
    
    results = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d")
            
            if hist.empty:
                continue
                
            current_price = hist['Close'].iloc[-1]
            prev_close = info.get('previousClose', current_price)
            change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
            
            # 한국 종목은 .KS 제거한 순수 코드로 매칭
            clean_symbol = symbol.replace(".KS", "") if ".KS" in symbol else symbol
            is_active = clean_symbol in active_symbols or symbol in active_symbols or symbol == "QQQ"
            
            results.append({
                "symbol": symbol,
                "name": info.get('shortName', symbol),
                "marketCap": info.get('marketCap', 0),
                "price": round(current_price, 2),
                "change": round(change_percent, 2),
                "isActive": is_active,
                "currency": currency
            })
        except Exception as e:
            logger.warning(f"Failed to fetch data for {symbol}: {e}")
            continue
    
    return {
        "symbols": results, 
        "timestamp": datetime.now().isoformat(),
        "market": market.upper(),
        "currency": currency
    }

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
