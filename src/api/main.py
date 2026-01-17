from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import asyncio
import json
import os
import logging
import asyncpg
import yaml
from datetime import datetime
from typing import List, Optional, Dict
from .auth import verify_api_key
from .routes import system
from .routes import virtual
from src.broker.virtual import VirtualExchange

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Antigravity API", version="1.0.0")

# Register Routers
app.include_router(system.router)
app.include_router(virtual.router)

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

# Global Configuration Cache
SYMBOLS_CACHE: Dict[str, Dict] = {}

def load_config():
    """로드된 YAML 설정 파일들로부터 심볼 정보를 읽어옴"""
    global SYMBOLS_CACHE
    try:
        config_dir = "configs"
        for filename in ["kr_symbols.yaml", "us_symbols.yaml"]:
            path = os.path.join(config_dir, filename)
            if os.path.exists(path):
                with open(path, "r") as f:
                    config = yaml.safe_load(f)
                    market = config.get("market", "UNKNOWN")
                    
                    # 1. Indices
                    for item in config.get("symbols", {}).get("indices", []):
                        SYMBOLS_CACHE[item["symbol"]] = {**item, "category": "MARKET"}
                    
                    # 2. Leverage
                    for item in config.get("symbols", {}).get("leverage", []):
                        SYMBOLS_CACHE[item["symbol"]] = {**item, "category": "MARKET"}
                        
                    # 3. Stocks (from sectors)
                    for sector_name, sector_data in config.get("symbols", {}).get("sectors", {}).items():
                        # Sector ETF also MARKET (if present)
                        if "etf" in sector_data:
                            SYMBOLS_CACHE[sector_data["etf"]["symbol"]] = {**sector_data["etf"], "category": "MARKET"}
                        
                        for stock in sector_data.get("top3", []):
                            SYMBOLS_CACHE[stock["symbol"]] = {**stock, "category": "STOCK"}
        
        logger.info(f"✅ Loaded {len(SYMBOLS_CACHE)} symbols from configuration files.")
    except Exception as e:
        logger.error(f"❌ Failed to load config: {e}")

@app.on_event("startup")
async def startup_event():
    global db_pool
    logger.info("🚀 Starting API server...")
    # 0. Load Symbols
    load_config()
    # Redis 구독 타스크 시작
    asyncio.create_task(redis_subscriber())
    asyncio.create_task(virtual_redis_subscriber())  # Virtual trading events
    # DB 커넥션 풀 초기화
    try:
        logger.info(f"📊 Connecting to DB: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        db_pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        # Attach to app state for routers
        app.state.db_pool = db_pool
        logger.info("✅ Database Pool initialized successfully!")
        
        # Initialize VirtualExchange
        db_config = {
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_NAME,
            'host': DB_HOST,
            'port': int(DB_PORT)
        }
        virtual.virtual_exchange = VirtualExchange(db_config, account_id=1)
        await virtual.virtual_exchange.connect()
        logger.info("✅ VirtualExchange initialized!")
        
        # Diagnostic: Check tables
        async with db_pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE '%candle%'
            """)
            logger.info(f"🔍 Found {len(tables)} candle-related tables: {[dict(r) for r in tables]}")
            
    except Exception as e:
        logger.error(f"❌ DB Pool Init Failed: {e}")

async def redis_subscriber():
    """Redis Pub/Sub 메시지를 브로드캐스트하는 타스크"""
    try:
        r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("market_ticker", "market_orderbook", "news_alert", "system_alerts", "system.metrics")
        logger.info("Connected to Redis Pub/Sub.")

        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.broadcast(message["data"])
    except Exception as e:
        logger.error(f"Redis Subscriber Exception: {e}")

async def virtual_redis_subscriber():
    """가상 거래 이벤트를 WebSocket으로 전달하는 타스크"""
    try:
        r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("virtual.execution", "virtual.account", "virtual.position")
        logger.info("Connected to Virtual Trading Redis Pub/Sub.")

        async for message in pubsub.listen():
            if message["type"] == "message":
                # Broadcast virtual trading events
                await manager.broadcast(message["data"])
    except Exception as e:
        logger.error(f"Virtual Redis Subscriber Exception: {e}")

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
async def get_recent_candles(symbol: str, limit: int = 200, interval: str = "1d"):
    """최근 분봉/일봉(Candle) 데이터 조회 (Continuous Aggregates 활용)"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Dynamic table/view selection based on interval
    # Updated: 2026-01-15 to use TimescaleDB Continuous Aggregates
    # Dynamic table/view selection based on interval
    # Updated: 2026-01-15 - Target Server Schema (Continuous Aggregates) with Local Fallback
    table_map = {
        "1m": "candles_1m",
        "5m": "market_candles_5m",
        "15m": "market_candles_15m",
        "1h": "market_candles_1h",
        "1d": "market_candles_1d"
    }
    
    table_name = table_map.get(interval)
    if not table_name:
        raise HTTPException(status_code=400, detail=f"Invalid interval: {interval}. Supported: 1m, 5m, 15m, 1h, 1d")
    
    async with db_pool.acquire() as conn:
        try:
            # Check if target is raw table or aggregate (Raw uses 'time', Agg uses 'bucket')
            # Updated: 2026-01-15 - Dual Source Strategy (View + Fallback Table)
            # If interval is 1m, we query BOTH and UNION them to fill gaps
            
            if interval == '1m':
                query = f"""
                    WITH combined_data AS (
                        SELECT time, open, high, low, close, volume, 1 as priority
                        FROM candles_1m
                        WHERE symbol = $1

                        UNION ALL

                        SELECT time, open, high, low, close, volume, 2 as priority
                        FROM market_candles
                        WHERE symbol = $1 AND interval = '1m'
                    )
                    SELECT time, open, high, low, close, volume
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY time ORDER BY priority ASC) as rn
                        FROM combined_data
                    ) sub
                    WHERE rn = 1
                    ORDER BY time DESC
                    LIMIT $2
                """
            else:
                # Existing logic for other intervals (or strictly table mapped)
                # For local development: query market_candles directly with interval filter
                query = f"""
                    SELECT time, open, high, low, close, volume
                    FROM market_candles
                    WHERE symbol = $1 AND interval = $3
                    ORDER BY time DESC
                    LIMIT $2
                """
                
            logger.info(f"Executing query on market_candles for {symbol} @ {interval}")
            # Pass interval as third parameter for non-1m queries
            if interval == '1m':
                rows = await conn.fetch(query, symbol, limit)
            else:
                rows = await conn.fetch(query, symbol, limit, interval)
            
            return [dict(r) for r in reversed(rows)]
        except Exception as e:
            logger.error(f"Failed to query {table_name}: {e}")
            raise e

@app.get("/api/v1/inspector/latest", dependencies=[Depends(verify_api_key)])
async def get_latest_inserts(limit: int = 50):
    """최근 DB에 적재된 틱/로그 데이터 조회 (Data Inspector)"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    async with db_pool.acquire() as conn:
        # market_ticks 테이블에서 최근 데이터 조회
        # 주의: market_ticks는 Hypertable이므로 time 컬럼 기준 정렬이 빠름
        rows = await conn.fetch("""
            SELECT time, symbol, price, volume, change 
            FROM market_ticks 
            ORDER BY time DESC 
            LIMIT $1
        """, limit)
        
        return [dict(r) for r in rows]

@app.get("/api/v1/market-map/{market}", dependencies=[Depends(verify_api_key)])
async def get_market_map(market: str = "us"):
    """
    시장별 Treemap 데이터 조회 (DB 기반, 수집된 데이터 한정)
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    results = []
    
    async with db_pool.acquire() as conn:
        # 최근 수집된 일봉 데이터 기준
        # 1. 대상 심볼 조회 (최근 30일간 1d 캔들이 있는 모든 종목)
        rows = await conn.fetch("""
            WITH RecentCandles AS (
                SELECT 
                    symbol, 
                    time, 
                    close, 
                    volume,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time DESC) as rn
                FROM market_candles 
                WHERE interval = '1d' AND time > NOW() - INTERVAL '30 days'
            )
            SELECT 
                t1.symbol, 
                t1.close as current_price, 
                t1.volume,
                t2.close as prev_price
            FROM RecentCandles t1
            LEFT JOIN RecentCandles t2 ON t1.symbol = t2.symbol AND t2.rn = 2
            WHERE t1.rn = 1
        """)
        
        for row in rows:
            symbol = row['symbol']
            curr = float(row['current_price'])
            prev = float(row['prev_price']) if row['prev_price'] else curr
            
            value_factor = float(row['volume']) * curr
            change_rate = ((curr - prev) / prev * 100) if prev > 0 else 0.0
            
            # Dynamic Info from Cache
            info = SYMBOLS_CACHE.get(symbol, {"name": symbol, "category": "STOCK"})
            display_name = info.get("name", symbol)
            category = info.get("category", "STOCK")

            results.append({
                "symbol": symbol,
                "name": display_name, 
                "marketCap": value_factor, 
                "price": curr,
                "prevPrice": prev,
                "change": round(change_rate, 2), # Keep for legacy compatibility
                "isActive": True,
                "currency": "KRW",
                "category": category
            })

    return {
        "symbols": results, 
        "timestamp": datetime.now().isoformat(),
        "market": "collected",
        "currency": "KRW"
    }

@app.get("/api/v1/indices/performance", dependencies=[Depends(verify_api_key)])
async def get_indices_performance():
    """지수/ETF 성과 데이터 조회 (SectorPerformance용)"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    results = []
    # MARKET 카테고리만 필터링
    target_symbols = [s for s, info in SYMBOLS_CACHE.items() if info["category"] == "MARKET"]
    
    if not target_symbols:
        return []

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            WITH RecentRel AS (
                SELECT 
                    symbol, 
                    time, 
                    close,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time DESC) as rn
                FROM market_candles
                WHERE interval = '1d' AND symbol = ANY($1)
            )
            SELECT t1.symbol, t1.close as curr, t2.close as prev
            FROM RecentRel t1
            LEFT JOIN RecentRel t2 ON t1.symbol = t2.symbol AND t2.rn = 2
            WHERE t1.rn = 1
        """, target_symbols)

        for row in rows:
            info = SYMBOLS_CACHE.get(row["symbol"], {})
            curr = float(row["curr"])
            prev = float(row["prev"]) if row["prev"] else curr
            return_rate = ((curr - prev) / prev * 100) if prev > 0 else 0.0
            
            results.append({
                "name": info.get("name", row["symbol"]),
                "etfSymbol": row["symbol"],
                "returnRate": round(return_rate, 2)
            })

    # 정렬: 수익률 내림차순
    return sorted(results, key=lambda x: x["returnRate"], reverse=True)

@app.get("/api/v1/health")
async def health_check():
    """
    기본 헬스 체크 - DB/Redis 연결 상태 및 응답 시간 확인
    """
    import time

    # Redis 상태 확인
    redis_status = False
    redis_ms = 0
    try:
        start = time.time()
        r = redis.from_url(REDIS_URL, socket_timeout=2.0)
        await r.ping()
        redis_ms = int((time.time() - start) * 1000)
        redis_status = True
        await r.close()
    except Exception:
        pass

    # DB 상태 확인 (실제 쿼리)
    db_status = False
    db_ms = 0
    try:
        if db_pool:
            start = time.time()
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ms = int((time.time() - start) * 1000)
            db_status = True
    except Exception:
        pass

    # 전체 상태 판정
    if db_status and redis_status:
        status = "healthy"
    elif db_status or redis_status:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "db": {"connected": db_status, "response_ms": db_ms},
        "redis": {"connected": redis_status, "response_ms": redis_ms},
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/health/detailed")
async def health_check_detailed():
    """
    상세 헬스 체크 - 시스템 전체 상태 (DB, Redis, Collectors, Sentinel)
    """
    import time

    result = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "database": {},
        "redis": {},
        "collectors": {},
        "sentinel": {}
    }

    # 1. Database 상태
    try:
        if db_pool:
            start = time.time()
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                db_ms = int((time.time() - start) * 1000)

                # 최근 5분 데이터 수
                recent_ticks = await conn.fetchval(
                    "SELECT COUNT(*) FROM market_ticks WHERE time > NOW() - INTERVAL '5 minutes'"
                )

                # 가장 최근 데이터 시간
                last_time = await conn.fetchval(
                    "SELECT MAX(time) FROM market_ticks"
                )
                last_age_sec = 0
                if last_time:
                    last_age_sec = int((datetime.now(last_time.tzinfo) - last_time).total_seconds())

                result["database"] = {
                    "status": "connected",
                    "response_ms": db_ms,
                    "recent_ticks_5m": recent_ticks or 0,
                    "last_data_age_sec": last_age_sec
                }
        else:
            result["database"] = {"status": "disconnected", "response_ms": 0}
            result["status"] = "degraded"
    except Exception as e:
        result["database"] = {"status": "error", "error": str(e)}
        result["status"] = "degraded"

    # 2. Redis 상태
    try:
        start = time.time()
        r = redis.from_url(REDIS_URL, socket_timeout=2.0)
        await r.ping()
        redis_ms = int((time.time() - start) * 1000)

        # 메모리 사용량
        info = await r.info("memory")
        memory_mb = round(info.get("used_memory", 0) / 1024 / 1024, 2)

        # 활성 채널
        channels = await r.pubsub_channels()
        channel_list = [ch.decode() if isinstance(ch, bytes) else ch for ch in channels]

        await r.close()

        result["redis"] = {
            "status": "connected",
            "response_ms": redis_ms,
            "memory_mb": memory_mb,
            "channels": channel_list
        }
    except Exception as e:
        result["redis"] = {"status": "error", "error": str(e)}
        result["status"] = "degraded"

    # 3. Collectors 상태 (Redis에서 마지막 업데이트 시간 조회)
    try:
        r = redis.from_url(REDIS_URL, socket_timeout=2.0)

        # Sentinel이 저장한 마지막 데이터 시간 조회
        kr_last = await r.get("collector:kr:last_update")
        us_last = await r.get("collector:us:last_update")

        result["collectors"] = {
            "kr": {
                "active": kr_last is not None,
                "last_update": kr_last.decode() if kr_last else None
            },
            "us": {
                "active": us_last is not None,
                "last_update": us_last.decode() if us_last else None
            }
        }

        await r.close()
    except Exception:
        result["collectors"] = {"kr": {"active": False}, "us": {"active": False}}

    # 4. Sentinel 상태 (Redis에서 조회)
    try:
        r = redis.from_url(REDIS_URL, socket_timeout=2.0)

        sentinel_status = await r.get("sentinel:status")
        circuit_breaker = await r.get("sentinel:circuit_breaker")
        last_alert = await r.get("sentinel:last_alert")

        result["sentinel"] = {
            "status": sentinel_status.decode() if sentinel_status else "unknown",
            "circuit_breaker": circuit_breaker.decode() if circuit_breaker else "unknown",
            "last_alert": last_alert.decode() if last_alert else None
        }

        await r.close()
    except Exception:
        result["sentinel"] = {"status": "unknown", "circuit_breaker": "unknown"}

    # 전체 상태 최종 판정
    if result["database"].get("status") != "connected" or result["redis"].get("status") != "connected":
        result["status"] = "unhealthy" if result["status"] == "degraded" else "degraded"

    return result

@app.get("/api/v1/analytics/correlation", dependencies=[Depends(verify_api_key)])
async def get_correlation_matrix(days: int = 30):
    """
    최근 N일간 종가 기준 상관관계 매트릭스 계산
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    import pandas as pd
    import numpy as np
    
    async with db_pool.acquire() as conn:
        # 최근 N일간의 모든 1d 캔들 가져오기
        # Pivot을 위해 데이터를 가져와서 Pandas로 처리
        rows = await conn.fetch("""
            SELECT time, symbol, close
            FROM market_candles 
            WHERE interval = '1d' AND time > NOW() - INTERVAL '60 days' 
            ORDER BY time ASC
        """)
        
        if not rows:
             return {"nodes": [], "links": []}

        # Convert to DataFrame
        df = pd.DataFrame([dict(r) for r in rows], columns=['time', 'symbol', 'close'])
        
        # Pivot: Index=Time, Columns=Symbol, Values=Close
        pivot_df = df.pivot_table(index='time', columns='symbol', values='close')
        
        # 최근 'days' 만큼 슬라이싱 (데이터가 충분하지 않을 수 있으므로 60일치 가져와서 뒤에서 자름)
        pivot_df = pivot_df.tail(days)
        
        # Forward fill missing values (휴장일 등) -> Drop duplicate cols if any
        pivot_df = pivot_df.ffill().dropna(axis=1) # 데이터가 너무 없는 종목은 제외

        # Calculate PCT Change for correlation (가격 절대값이 아닌 변화율의 상관관계가 더 의미있음)
        pct_df = pivot_df.pct_change().dropna()

        # Calculate Correlation Matrix
        corr_matrix = pct_df.corr()
        
        # Format for D3/Recharts Graph: Nodes & Links
        # Nodes: Symbols
        # Links: Significant correlations (|r| > 0.5)
        
        nodes = [{"id": sym, "group": 1} for sym in corr_matrix.columns]
        links = []
        
        for i, sym1 in enumerate(corr_matrix.columns):
            for j, sym2 in enumerate(corr_matrix.columns):
                if i >= j: continue # Avoid duplicates and self-loop
                val = corr_matrix.iloc[i, j]
                if abs(val) > 0.5: # Filter weak correlations
                    links.append({
                        "source": sym1,
                        "target": sym2,
                        "value": round(val, 2)
                    })
                    
        return {
            "nodes": nodes,
            "links": links,
            "matrix": corr_matrix.reset_index().to_dict(orient='records'), # Full matrix if needed
            "period": f"Last {days} Days"
        }

# --- WebSocket Endpoint ---

@app.get("/system/info")
async def get_system_info():
    """시스템 기본 정보 조회 (Environment Identifier)"""
    import socket
    return {
        "env": os.getenv("APP_ENV", "development"),
        "hostname": socket.gethostname(),
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/virtual")
async def virtual_websocket_endpoint(websocket: WebSocket, api_key: Optional[str] = None):
    """Virtual Trading WebSocket - Real-time updates for orders, positions, account"""
    # Simple auth check (in production, use proper token validation)
    if not api_key or api_key != API_AUTH_SECRET:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await manager.connect(websocket)
    logger.info("Virtual Trading WebSocket client connected")
    try:
        while True:
            # Keep connection alive, actual data comes from Redis subscriber
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Virtual Trading WebSocket client disconnected")

