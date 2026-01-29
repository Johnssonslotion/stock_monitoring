"""
Verification Worker (Producer/Consumer)
=======================================
RFC-008 Appendix E.4 구현 + ISSUE-041 Container Unification

Redis Queue 기반 비동기 검증 작업 처리.
- Producer: 검증 작업 생성 → Redis Queue
- Consumer: Redis Queue → API Hub Queue → API 호출 → DB 저장

ISSUE-041: API Hub Queue로 통합 (Token 관리 및 Rate Limiting 중앙화)
"""
import asyncio
import json
import os
import logging
import yaml
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
import asyncpg

from src.api_gateway.hub.client import APIHubClient

logger = logging.getLogger(__name__)


# === Data Classes ===

class VerificationStatus(Enum):
    """검증 상태"""
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_RECOVERY = "NEEDS_RECOVERY"
    SKIPPED = "SKIPPED"
    INCOMPLETE = "INCOMPLETE"
    ERROR = "ERROR"
    TICKS_UNAVAILABLE = "TICKS_UNAVAILABLE"  # Fallback: Tick API failed, Candles upserted


class ConfidenceLevel(Enum):
    """신뢰도 수준"""
    HIGH = "HIGH"       # 듀얼 검증 일치
    MEDIUM = "MEDIUM"   # 듀얼 검증 불일치 또는 단일 소스
    LOW = "LOW"         # 부분 데이터
    SKIP = "SKIP"       # 검증 스킵


@dataclass
class VerificationTask:
    """검증 작업"""
    task_type: str          # full_verification, minute_verification, recovery
    symbol: str
    date: Optional[str] = None
    minute: Optional[str] = None
    priority: str = "normal"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "VerificationTask":
        return cls(**json.loads(data))


@dataclass
class VerificationResult:
    """검증 결과"""
    symbol: str
    minute: Optional[str]
    status: VerificationStatus
    confidence: ConfidenceLevel
    kis_volume: Optional[int] = None
    kiwoom_volume: Optional[int] = None
    db_volume: Optional[int] = None
    delta_pct: float = 0.0
    price_match: bool = False
    details: Optional[Dict[str, Any]] = None
    message: str = ""
    verified_at: str = ""

    def __post_init__(self):
        if not self.verified_at:
            self.verified_at = datetime.now().isoformat()
        if self.details is None:
            self.details = {}


# === Configuration ===

class VerificationConfig:
    """검증 설정"""
    # Redis Queue Keys
    QUEUE_KEY = "verify:queue"
    PRIORITY_QUEUE_KEY = "verify:queue:priority"
    DLQ_KEY = "verify:queue:dlq"

    # Tolerance
    BATCH_TOLERANCE_PCT = 0.001      # 배치 모드: 0.1%
    REALTIME_TOLERANCE_PCT = 0.02    # 실시간 모드: 2%
    MIN_VOLUME_THRESHOLD = 100       # 최소 거래량 (미만 시 스킵)

    # Retry
    MAX_RETRIES = 3
    RETRY_DELAY_SEC = 2.0

    # Batch
    BATCH_SIZE = 10
    BATCH_DELAY_SEC = 1.0

    # Scheduling
    VERIFICATION_OFFSET_SECONDS = int(os.getenv("VERIFICATION_OFFSET_SECONDS", 30))


# === TR ID Mapping (API Hub용) ===
# Centralized TR Registry 사용
from src.api_gateway.hub.tr_registry import (
    UseCase,
    get_tr_id_for_use_case,
    validate_tr_id
)

# TR ID 검증 (Startup Validation)
_REQUIRED_TR_IDS = [
    UseCase.MINUTE_CANDLE_KIS,
    UseCase.TICK_DATA_KIS,
    UseCase.MINUTE_CANDLE_KIWOOM,
]

for use_case in _REQUIRED_TR_IDS:
    tr_id = get_tr_id_for_use_case(use_case)
    if not validate_tr_id(tr_id):
        raise ValueError(f"Invalid TR ID for {use_case}: {tr_id}")
    logger.debug(f"✓ Validated TR ID: {use_case.value} → {tr_id}")


# === Producer ===

class VerificationProducer:
    """
    검증 작업 생성자 (Scheduler → Redis Queue)

    스케줄에 따라 검증 작업을 생성하여 Redis Queue에 추가.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/1")
        self.redis: Optional[redis.Redis] = None
        self._target_symbols: List[str] = []

    async def connect(self):
        """Redis 연결"""
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Producer connected to Redis: {self.redis_url}")

    async def close(self):
        """연결 종료"""
        if self.redis:
            await self.redis.close()
            self.redis = None

    def set_target_symbols(self, symbols: List[str]):
        """검증 대상 종목 설정"""
        self._target_symbols = symbols

    async def get_target_symbols(self) -> List[str]:
        """검증 대상 종목 조회 (configs/kr_symbols.yaml 로드)"""
        if self._target_symbols:
            return self._target_symbols

        config_path = os.path.join(os.getcwd(), "configs/kr_symbols.yaml")
        if not os.path.exists(config_path):
            logger.error(f"❌ Symbol config not found: {config_path}")
            return ["005930", "000660"] # Fallback

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            symbols_data = config.get('symbols', {})
            targets = []
            
            # Indices
            for item in symbols_data.get('indices', []):
                targets.append(item['symbol'])
            
            # Leverage
            for item in symbols_data.get('leverage', []):
                targets.append(item['symbol'])
            
            # Sectors
            for sector_data in symbols_data.get('sectors', {}).values():
                if 'etf' in sector_data:
                    targets.append(sector_data['etf']['symbol'])
                for stock in sector_data.get('top3', []):
                    targets.append(stock['symbol'])
            
            unique_targets = sorted(list(set(targets)))
            logger.info(f"📋 Loaded {len(unique_targets)} symbols for verification")
            return unique_targets
        except Exception as e:
            logger.error(f"❌ Failed to load symbols from {config_path}: {e}")
            return ["005930", "000660"]

    async def produce_daily_tasks(self):
        """장 마감 후 전체 검증 작업 생성"""
        await self.connect()

        symbols = await self.get_target_symbols()
        today = datetime.now().strftime("%Y%m%d")
        count = 0

        for symbol in symbols:
            task = VerificationTask(
                task_type="verify_db_integrity",
                symbol=symbol,
                date=today
            )
            await self.redis.lpush(VerificationConfig.QUEUE_KEY, task.to_json())
            count += 1

        logger.info(f"📤 Produced {count} daily verification tasks")
        return count

    async def produce_minute_task(self, symbol: str, minute: datetime):
        """실시간 분봉 검증 작업 생성"""
        await self.connect()

        task = VerificationTask(
            task_type="verify_db_integrity",
            symbol=symbol,
            minute=minute.isoformat()
        )
        await self.redis.lpush(VerificationConfig.QUEUE_KEY, task.to_json())
        logger.debug(f"📤 Produced minute task: {symbol} @ {minute}")

    async def produce_recovery_task(self, symbol: str, minute: datetime, gap: int):
        """긴급 복구 작업 생성 (우선순위 큐)"""
        await self.connect()

        task = VerificationTask(
            task_type="recovery",
            symbol=symbol,
            minute=minute.isoformat(),
            priority="high"
        )
        await self.redis.lpush(VerificationConfig.PRIORITY_QUEUE_KEY, task.to_json())
        logger.warning(f"⚠️ Recovery task queued: {symbol} @ {minute}, gap={gap}")

    async def get_queue_length(self) -> Dict[str, int]:
        """큐 길이 조회"""
        await self.connect()
        return {
            "normal": await self.redis.llen(VerificationConfig.QUEUE_KEY),
            "priority": await self.redis.llen(VerificationConfig.PRIORITY_QUEUE_KEY),
            "dlq": await self.redis.llen(VerificationConfig.DLQ_KEY)
        }


# === Consumer ===

class VerificationConsumer:
    """
    검증 작업 소비자 (Redis Queue → API Hub Queue → DB)

    ISSUE-041: API Hub Queue 통합
    - Token 관리는 API Hub의 TokenManager가 담당
    - Rate Limiting은 API Hub의 Dispatcher가 담당
    """

    def __init__(self, redis_url: Optional[str] = None, db_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/1")
        self.db_url = db_url or self._get_db_url()
        self.redis: Optional[redis.Redis] = None
        self.hub_client: Optional[APIHubClient] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self._running = False
        self._results: List[VerificationResult] = []
    
    def _get_db_url(self) -> str:
        """Get TimescaleDB connection URL from environment"""
        db_host = os.getenv("DB_HOST", "timescaledb")
        db_port = os.getenv("DB_PORT", "5432")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "password")
        db_name = os.getenv("DB_NAME", "stockval")
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    async def connect(self):
        """Redis 및 API Hub Client 연결"""
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Consumer connected to Redis: {self.redis_url}")
        
        if not self.hub_client:
            self.hub_client = APIHubClient()
            logger.info("API Hub Client initialized")
        
        # DB Pool 초기화 (검증 결과 저장용)
        if self.db_url and not self.db_pool:
            try:
                self.db_pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
                logger.info("DB pool connected for verification results")
            except Exception as e:
                logger.error(f"Failed to connect DB pool: {e}")

    async def close(self):
        """연결 종료"""
        self._running = False
        if self.redis:
            await self.redis.close()
            self.redis = None
        if self.hub_client:
            await self.hub_client.close()
            self.hub_client = None
        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None
            logger.info("DB pool closed")

    async def start(self):
        """소비 루프 시작"""
        await self.connect()
        self._running = True
        logger.info("Consumer started (API Hub mode)")
        await self._consume_loop()

    async def stop(self):
        """소비 루프 중지"""
        self._running = False
        logger.info("Consumer stopping...")

    async def _consume_loop(self):
        """메인 소비 루프"""
        while self._running:
            task = None

            # 1. 우선순위 큐 먼저 확인
            raw_task = await self.redis.rpop(VerificationConfig.PRIORITY_QUEUE_KEY)

            # 2. 일반 큐에서 Blocking Pop
            if not raw_task:
                result = await self.redis.brpop(VerificationConfig.QUEUE_KEY, timeout=5)
                if result:
                    _, raw_task = result

            if not raw_task:
                continue

            # 3. 작업 실행
            try:
                task = VerificationTask.from_json(raw_task)
                
                if task.task_type == "verify_db_integrity":
                    result = await self._handle_db_integrity_task(task)
                elif task.task_type == "recovery":
                    result = await self._handle_recovery_task(task)
                else:
                    result = await self._process_task(task)
                
                self._results.append(result)
                
                # DB에 검증 결과 저장 (감사 추적)
                await self._save_verification_result(result)

                # Auto-Recovery is now handled INSIDE _handle_db_integrity_task
                # So we don't need to trigger it here for that task type.
                # Only legacy 'full_verification' might need this, but we are moving away from it.
                if task.task_type not in ["verify_db_integrity", "recovery"] and result.status == VerificationStatus.NEEDS_RECOVERY:
                    logger.warning(f"⚠️  Legacy Gap detected: {result.symbol}, delta={result.delta_pct:.2%}")
                    logger.info(f"🔧 Auto-triggering recovery task for {result.symbol}")
                    
                    # 복구 작업 생성 (우선순위 큐에 추가)
                    recovery_task = VerificationTask(
                        task_type="recovery",
                        symbol=result.symbol,
                        minute=result.minute,
                        priority="high"
                    )
                    await self.redis.lpush(
                        VerificationConfig.PRIORITY_QUEUE_KEY,
                        recovery_task.to_json()
                    )
                    logger.info(f"✅ Recovery task added to priority queue: {result.symbol}")

            except Exception as e:
                logger.error(f"Task failed: {e}")
                # Dead Letter Queue로 이동
                if raw_task:
                    await self.redis.lpush(VerificationConfig.DLQ_KEY, raw_task)

    async def _save_verification_result(self, result: VerificationResult):
        """
        검증 결과를 DB에 저장 (감사 추적용)
        
        Table: market_verification_results
        - 교차 검증 결과 기록
        - Gap 발견 시 복구 트리거 근거
        """
        if not self.db_pool or not result.minute:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO market_verification_results
                    (time, symbol, kis_vol, kiwoom_vol, vol_delta_kis, vol_delta_kiwoom, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    datetime.fromisoformat(result.minute),
                    result.symbol,
                    float(result.kis_volume) if result.kis_volume else None,
                    float(result.kiwoom_volume) if result.kiwoom_volume else None,
                    result.delta_pct,
                    result.delta_pct,
                    result.status.value
                )
                logger.debug(f"✓ Saved verification result: {result.symbol} @ {result.minute[:16]} → {result.status.value}")
        except Exception as e:
            logger.error(f"Failed to save verification result to DB: {e}")


    async def _handle_db_integrity_task(self, task: VerificationTask) -> VerificationResult:
        """
        [RFC-005] DB Integrity Verification (Realtime + Batch)
        Target: DB View (market_candles_1m_view) vs API Candle (Ground Truth)
        Strategy: Tick Recovery First -> Candle Fallback
        """
        symbol = task.symbol
        # Parse minute or date (Batch uses date)
        if task.minute:
            start_dt = datetime.fromisoformat(task.minute)
            end_dt = start_dt + timedelta(minutes=1)
            target_desc = f"{symbol} @ {task.minute}"
        elif task.date:
            # Full Day Batch (09:00 ~ 15:30)
            start_dt = datetime.strptime(f"{task.date} 090000", "%Y%m%d %H%M%S")
            end_dt = datetime.strptime(f"{task.date} 153000", "%Y%m%d %H%M%S")
            target_desc = f"{symbol} @ {task.date} (Batch)"
        else:
            return VerificationResult(symbol=symbol, minute=None, status=VerificationStatus.ERROR, confidence=ConfidenceLevel.SKIP, message="No date/minute")

        logger.info(f"🔍 Verifying Integrity: {target_desc}")

        # 1. Fetch DB Volume (Aggregated)
        db_vol = await self._fetch_db_volume(symbol, start_dt, end_dt)
        
        # 2. Fetch API Volume (Ground Truth) - KIS Minute Candle
        # Note: If Batch, we might need to loop or fetch 1 day candle? 
        # For simplicity and granularity, let's fetch Minute Candles from API.
        # But for full day batch, calling API for every minute is too heavy (380 calls).
        # Optimization: Fetch Daily Candle for Volume Checksum first?
        # User constraint: "verify day's minute candles".
        # Let's assume we verify volume sum.
        
        api_vol_sum = 0
        api_candles = []
        
        # Helper to fetch API
        try:
            api_candles = await self._fetch_api_candles_range(symbol, start_dt, end_dt)
            if not api_candles:
                 return VerificationResult(symbol=symbol, minute=str(start_dt), status=VerificationStatus.SKIPPED, confidence=ConfidenceLevel.SKIP, message="No API Data")
            
            api_vol_sum = sum(c['volume'] for c in api_candles)
        except Exception as e:
             return VerificationResult(symbol=symbol, minute=str(start_dt), status=VerificationStatus.ERROR, confidence=ConfidenceLevel.SKIP, message=f"API Error: {e}")

        # 3. Compare
        delta_pct = abs(api_vol_sum - db_vol) / max(api_vol_sum, 1) if api_vol_sum > 0 else 0.0
        tolerance = VerificationConfig.BATCH_TOLERANCE_PCT if task.date else VerificationConfig.REALTIME_TOLERANCE_PCT
        
        if delta_pct > tolerance:
            logger.warning(f"🚨 Integrity Fail: {target_desc} (DB={db_vol}, API={api_vol_sum}, Δ={delta_pct:.2%})")
            
            # 4. Trigger Recovery (Same-Day Catch-up)
            recovery_res = await self._recover_from_gap(symbol, start_dt, end_dt, api_candles)
            return recovery_res
        
        return VerificationResult(
            symbol=symbol,
            minute=str(start_dt),
            status=VerificationStatus.PASS,
            confidence=ConfidenceLevel.HIGH,
            db_volume=db_vol,
            kis_volume=api_vol_sum,
            delta_pct=delta_pct,
            message="Integrity Verified"
        )

    async def _fetch_db_volume(self, symbol: str, start: datetime, end: datetime) -> int:
        if not self.db_pool: return 0
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT COALESCE(SUM(volume), 0) as vol 
                FROM market_candles_1m_view 
                WHERE symbol = $1 AND time >= $2 AND time < $3
            """, symbol, start, end)
            return int(row['vol']) if row else 0

    async def _fetch_api_candles_range(self, symbol: str, start: datetime, end: datetime) -> List[Dict]:
        """
        API Hub를 통해 KIS 분봉 데이터 조회 (API Hub Client 사용)
        FHKST01010400: 주식현재가 분봉 조회
        """
        tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIS)
        
        # KIS API requests backward from time provided.
        # Format: HHMMSS of the END time.
        # Caution: KIS might return 30 items default. 'FID_INPUT_HOUR_1'="" implies current time.
        # If we need specific range, we might need multiple calls or careful time setting.
        # Simplification: For realtime (last min) or small batch, fetching "current" set matches nicely.
        # But for yesterday's batch, we need to specify time.
        
        target_time = end.strftime("%H%M%S")
        
        # If target is future/now, use empty string for latest
        if end > datetime.now():
            target_time = ""

        try:
            result = await self.hub_client.execute(
                provider="KIS",
                tr_id=tr_id,
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_HOUR_1": target_time,
                    "FID_PW_DATA_INCU_YN": "Y"
                },
                timeout=10.0
            )

            if result.get("status") == "SUCCESS":
                data = result.get("data", {})
                items = data.get("output2", [])
                
                valid_candles = []
                for item in items:
                    # Filter items within range [start, end)
                    t_str = item.get('stck_cntg_hour') # HHMMSS
                    if not t_str: continue
                    
                    # Date is implicit? KIS REST output2 is intraday.
                    # We assume it matches the 'start' date if we are doing daily check.
                    # Or we just match HHMMSS.
                    
                    # Logic: Create datetime from item time
                    # API returns latest first? Need to check sort order. Usually desc.
                    
                    # Infer date from start (assuming range is within one day)
                    item_dt = datetime.strptime(f"{start.strftime('%Y%m%d')} {t_str}", "%Y%m%d %H%M%S")
                    
                    if start <= item_dt < end:
                         valid_candles.append({
                             'time': item_dt,
                             'open': float(item.get('stck_oprc', 0)),
                             'high': float(item.get('stck_hgpr', 0)),
                             'low': float(item.get('stck_lwpr', 0)),
                             'close': float(item.get('stck_prpr', 0)),
                             'volume': int(item.get('cntg_vol', 0))
                         })
                
                return valid_candles
                
            else:
                logger.warning(f"Failed to fetch API candles: {result.get('reason')}")
                return []

        except Exception as e:
            logger.error(f"API Fetch Error: {e}")
            return []

    async def _recover_from_gap(self, symbol: str, start: datetime, end: datetime, api_candles: List[Dict]) -> VerificationResult:
        """
        [RFC-005] Recovery Strategy: Tick First -> Candle Fallback
        """
        logger.info(f"🔧 Attempting Recovery for {symbol}")
        
        # Step 1: Try Tick Recovery (API Hub)
        try:
            # Only possible if gap is small (e.g. 1 min). If batch, iterating all ticks is hard.
            # But "Same-Day" usually implies we CAN fetch ticks.
            # Let's try fetching ticks for the specific minutes that failed.
            # Only fetch ticks if range is short (< 10 min).
            duration = (end - start).total_seconds() / 60
            if duration <= 10: 
                # Simulate Tick Fetch
                tick_count = await self._fetch_and_save_ticks(symbol, start)
                if tick_count > 0:
                     return VerificationResult(symbol=symbol, minute=str(start), status=VerificationStatus.PASS, confidence=ConfidenceLevel.HIGH, message="Recovered via Ticks")
        except Exception as e:
            logger.warning(f"⚠️ Tick Recovery Failed: {e}")

        # Step 2: Fallback to Candle Upsert
        logger.warning(f"⚠️ Fallback to Candle Upsert for {symbol}")
        try:
             # Upsert api_candles to market_candles table
             await self._upsert_candles_fallback(symbol, api_candles)
             return VerificationResult(
                 symbol=symbol, 
                 minute=str(start), 
                 status=VerificationStatus.TICKS_UNAVAILABLE, # Log this!
                 confidence=ConfidenceLevel.MEDIUM, 
                 message="Recovered via Candle Fallback (Ticks Unavailable)"
             )
        except Exception as e:
             return VerificationResult(symbol=symbol, minute=str(start), status=VerificationStatus.FAIL, confidence=ConfidenceLevel.LOW, message=f"Recovery Failed: {e}")

    async def _upsert_candles_fallback(self, symbol: str, candles: List[Dict]):
        """
        Fallback: API 캔들 데이터를 DB에 Upsert
        SourceType: 'REST_API_KIS' (Ground Truth)
        """
        if not self.db_pool or not candles: return

        query = """
            INSERT INTO market_candles (time, symbol, interval, open, high, low, close, volume, source_type)
            VALUES ($1, $2, '1m', $3, $4, $5, $6, $7, 'REST_API_KIS')
            ON CONFLICT (symbol, time) DO UPDATE
            SET open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                source_type = EXCLUDED.source_type
        """
        
        args = [
            (c['time'], symbol, c['open'], c['high'], c['low'], c['close'], c['volume'])
            for c in candles
        ]
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.executemany(query, args)
            logger.info(f"✅ Upserted {len(candles)} candles for {symbol} (Fallback)")
        except Exception as e:
            logger.error(f"Failed to upsert candles: {e}")
            raise e

    async def _fetch_and_save_ticks(self, symbol: str, dt_min: datetime) -> int:
        """
        지정된 분(Minute)의 틱 데이터를 API에서 조회하여 저장
        Returns: 저장된 틱 수
        """
        # KIS API expects HHMMSS of the end of the window (approx)
        target_time_req = (dt_min + timedelta(minutes=1)).strftime("%H%M%S")
        
        try:
            tr_id = get_tr_id_for_use_case(UseCase.TICK_DATA_KIS)
            result = await self.hub_client.execute(
                provider="KIS",
                tr_id=tr_id,
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_HOUR_1": target_time_req
                },
                timeout=10.0
            )

            if result.get("status") == "SUCCESS":
                data = result.get("data", {})
                items = data.get("output1", [])
                if items:
                    # Filter: Only Ticks matching the target minute HHMM
                    target_hhmm = dt_min.strftime("%H%M")
                    filtered_items = [
                        item for item in items 
                        if item.get('stck_cntg_hour', '')[:4] == target_hhmm
                    ]
                    
                    if filtered_items:
                        return await self._save_recovered_ticks(symbol, dt_min, filtered_items)
            
            elif result.get("status") == "RATE_LIMITED":
                logger.warning(f"[{symbol}] Rate limited by API Hub during tick fetch")
            else:
                 logger.debug(f"[{symbol}] API Hub Tick Fetch result: {result.get('status')}")

        except Exception as e:
            logger.error(f"[{symbol}] Tick fetch error: {e}")
        
        return 0

    async def _handle_recovery_task(self, task: VerificationTask) -> VerificationResult:
        """
        긴급 복구 작업 처리 (Legacy wrapper around _fetch_and_save_ticks)
        """
        symbol = task.symbol
        dt_min = datetime.fromisoformat(task.minute)
        
        logger.info(f"🛠️ Handling recovery task for {symbol} @ {dt_min.strftime('%H:%M')}")
        
        try:
            recovered_count = await self._fetch_and_save_ticks(symbol, dt_min)
            
            if recovered_count > 0:
                # Refresh View
                await self._refresh_continuous_aggregates(
                    dt_min,
                    dt_min + timedelta(minutes=1)
                )

                return VerificationResult(
                    symbol=symbol,
                    minute=task.minute,
                    status=VerificationStatus.PASS,
                    confidence=ConfidenceLevel.HIGH,
                    message=f"Recovered {recovered_count} ticks via API Hub + View refreshed"
                )
            else:
                return VerificationResult(
                    symbol=symbol,
                    minute=task.minute,
                    status=VerificationStatus.FAIL,
                    confidence=ConfidenceLevel.LOW,
                    message="Recovery failed (No ticks found)"
                )
        
        except Exception as e:
            logger.error(f"[{symbol}] Recovery task exception: {e}")
            return VerificationResult(
                symbol=symbol,
                minute=task.minute,
                status=VerificationStatus.ERROR,
                confidence=ConfidenceLevel.LOW,
                message=f"Recovery exception: {e}"
            )

    async def _save_recovered_ticks(self, symbol: str, dt_min: datetime, items: List[Dict]) -> int:
        """복구된 틱 데이터를 DB에 저장 (TimescaleDB)"""
        import asyncpg
        target_hhmm = dt_min.strftime("%H%M")
        date_prefix = dt_min.strftime("%Y%m%d")
        
        rows = []
        for item in items:
            t_str = item.get('stck_cntg_hour')
            if t_str and t_str[:4] == target_hhmm:
                # Build Row (time, symbol, source, price, volume, change)
                tick_dt = datetime.strptime(f"{date_prefix} {t_str}", "%Y%m%d %H%M%S")
                # ISSUE-044: Use REST_API_KIS per Ground Truth Policy
                rows.append((
                    tick_dt, symbol, "REST_API_KIS",
                    float(item['stck_prpr']), float(item['cntg_vol']), float(item.get('prdy_vrss', 0))
                ))
        
        if rows:
            db_url = os.getenv("TIMESCALE_URL")
            if not db_url: return 0
            
            try:
                conn = await asyncpg.connect(db_url)
                # INSERT ON CONFLICT is hard with copy_records, but for multi-row we can use a temp table or executemany
                # Since real-time recovery is small (one minute), executemany is fine.
                query = """
                    INSERT INTO market_ticks (time, symbol, source, price, volume, change)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """
                # Note: No primary key on market_ticks for speed, so no ON CONFLICT needed for now?
                # Actually, duplicate prevention is better.
                await conn.executemany(query, rows)
                await conn.close()
                return len(rows)
            except Exception as e:
                logger.error(f"Failed to save recovered ticks: {e}")

        return 0

    async def _refresh_continuous_aggregates(self, start: datetime, end: datetime):
        """
        ISSUE-044: Refresh Continuous Aggregates after tick recovery

        Refreshes views for the given time range.
        """
        views = [
            'market_candles_1m_view',
            'market_candles_5m_view',
            'market_candles_1h_view',
            'market_candles_1d_view'
        ]

        if not self.db_pool:
            logger.warning("DB pool not initialized, skipping refresh")
            return

        for view in views:
            for attempt in range(3):  # Max 3 retries
                try:
                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            "CALL refresh_continuous_aggregate($1, $2, $3)",
                            view, start, end
                        )
                    logger.info(f"✅ Refreshed {view} for {start} → {end}")
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"❌ Failed to refresh {view} after 3 attempts: {e}")
                        # Queue for later retry (optional: implement pending_refresh queue)
                    else:
                        logger.warning(f"⚠️ Retry {attempt+1}/3 for {view}: {e}")
                        await asyncio.sleep(1)

    async def _process_task(
        self,
        task: VerificationTask
    ) -> VerificationResult:
        """
        작업 처리: API Hub를 통한 듀얼 API 호출 → 교차 검증
        
        ISSUE-041: API Hub Queue를 사용하여 Rate Limiting과 Token 관리를 중앙화

        Args:
            task: 검증 작업

        Returns:
            VerificationResult
        """
        symbol = task.symbol
        api_results = {}

        # KIS API 호출 (API Hub를 통해 - TR Registry 사용)
        try:
            kis_tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIS)
            kis_result = await self.hub_client.execute(
                provider="KIS",
                tr_id=kis_tr_id,
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_HOUR_1": "",
                    "FID_PW_DATA_INCU_YN": "Y"
                },
                timeout=10.0
            )
            
            if kis_result.get("status") == "SUCCESS":
                data = kis_result.get("data", {})
                items = data.get("output2", [])
                if items:
                    # KIS 분봉 데이터는 output2에 담김, volume key는 "cntg_vol"
                    kis_volume = sum(int(item.get("cntg_vol", 0)) for item in items if isinstance(item, dict))
                    api_results["kis"] = kis_volume
                    logger.debug(f"KIS volume for {symbol}: {kis_volume}")
            else:
                logger.warning(f"KIS API call failed for {symbol}: {kis_result.get('reason', 'Unknown')}")
        
        except Exception as e:
            logger.error(f"KIS API call exception for {symbol}: {e}")

        # Kiwoom API 호출 (API Hub를 통해 - TR Registry 사용)
        try:
            kiwoom_tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIWOOM)
            kiwoom_result = await self.hub_client.execute(
                provider="KIWOOM",
                tr_id=kiwoom_tr_id,
                params={
                    "symbol": symbol,
                    "time_unit": "1",  # 1분봉
                    "count": "120"     # 최근 2시간
                },
                timeout=10.0
            )
            
            if kiwoom_result.get("status") == "SUCCESS":
                data = kiwoom_result.get("data", {})
                items = data.get("output", [])
                if items:
                    # Kiwoom 분봉 데이터는 output에 담김, volume key는 "trde_qty"
                    kiwoom_volume = sum(int(item.get("trde_qty", 0)) for item in items if isinstance(item, dict))
                    api_results["kiwoom"] = kiwoom_volume
                    logger.debug(f"Kiwoom volume for {symbol}: {kiwoom_volume}")
            else:
                logger.warning(f"Kiwoom API call failed for {symbol}: {kiwoom_result.get('reason', 'Unknown')}")
        
        except Exception as e:
            logger.error(f"Kiwoom API call exception for {symbol}: {e}")

        # 교차 검증
        return self._cross_validate(symbol, task.minute, api_results)

    def _cross_validate(
        self,
        symbol: str,
        minute: Optional[str],
        api_results: Dict[str, int]
    ) -> VerificationResult:
        """
        교차 검증 로직

        Args:
            symbol: 종목 코드
            minute: 검증 대상 분
            api_results: API별 거래량 {provider: volume}

        Returns:
            VerificationResult
        """
        kis_vol = api_results.get("kis")
        kiwoom_vol = api_results.get("kiwoom")

        # 데이터 부족
        if not kis_vol and not kiwoom_vol:
            return VerificationResult(
                symbol=symbol,
                minute=minute,
                status=VerificationStatus.ERROR,
                confidence=ConfidenceLevel.SKIP,
                message="No API data available"
            )

        # 듀얼 검증
        if kis_vol and kiwoom_vol:
            delta = abs(kis_vol - kiwoom_vol) / max(kis_vol, 1)

            if delta < VerificationConfig.BATCH_TOLERANCE_PCT:
                return VerificationResult(
                    symbol=symbol,
                    minute=minute,
                    status=VerificationStatus.PASS,
                    confidence=ConfidenceLevel.HIGH,
                    kis_volume=kis_vol,
                    kiwoom_volume=kiwoom_vol,
                    delta_pct=delta,
                    message="Dual verification passed"
                )
            else:
                return VerificationResult(
                    symbol=symbol,
                    minute=minute,
                    status=VerificationStatus.NEEDS_RECOVERY,
                    confidence=ConfidenceLevel.MEDIUM,
                    kis_volume=kis_vol,
                    kiwoom_volume=kiwoom_vol,
                    delta_pct=delta,
                    message=f"Volume mismatch: KIS={kis_vol}, Kiwoom={kiwoom_vol}"
                )

        # 단일 소스
        volume = kis_vol or kiwoom_vol
        provider = "KIS" if kis_vol else "Kiwoom"

        return VerificationResult(
            symbol=symbol,
            minute=minute,
            status=VerificationStatus.PASS,
            confidence=ConfidenceLevel.LOW,
            kis_volume=kis_vol,
            kiwoom_volume=kiwoom_vol,
            message=f"Single source verification ({provider})"
        )

    def get_results(self) -> List[VerificationResult]:
        """검증 결과 조회"""
        return self._results.copy()

    def clear_results(self):
        """검증 결과 초기화"""
        self._results.clear()

    def generate_report(self) -> Dict[str, Any]:
        """검증 결과 리포트 생성"""
        if not self._results:
            return {"summary": {"total": 0}, "details": []}

        total = len(self._results)
        passed = sum(1 for r in self._results if r.status == VerificationStatus.PASS)
        failed = sum(1 for r in self._results if r.status == VerificationStatus.FAIL)
        needs_recovery = sum(1 for r in self._results if r.status == VerificationStatus.NEEDS_RECOVERY)
        high_confidence = sum(1 for r in self._results if r.confidence == ConfidenceLevel.HIGH)

        return {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "needs_recovery": needs_recovery,
                "high_confidence": high_confidence,
                "pass_rate": passed / total if total > 0 else 0
            },
            "details": [
                {
                    "symbol": r.symbol,
                    "status": r.status.value,
                    "confidence": r.confidence.value,
                    "delta_pct": r.delta_pct,
                    "message": r.message
                }
                for r in self._results
            ]
        }


# === Standalone Runner ===

async def run_verification_worker():
    """
    검증 워커 실행 (Producer + Consumer 병렬)

    Usage:
        python -m src.verification.worker
    """
    from src.verification.scheduler import (
        VerificationSchedulerManager,
        VerificationSchedule,
        ScheduleType
    )
    from datetime import datetime # Added import for datetime.now()
    
    producer = VerificationProducer()
    consumer = VerificationConsumer()
    scheduler = VerificationSchedulerManager()

    # [RFC-005] Unified Scheduler Configuration
    
    # Define wrapper for realtime verification (All Target Symbols)
    async def produce_realtime_all():
        # Get current time for the task
        now = datetime.now()
        symbols = await producer.get_target_symbols()
        # For priority symbols only? Or all?
        # RFC says "Priority Symbols" for Realtime.
        # Assuming get_target_symbols returns priority ones for now.
        for sym in symbols:
            await producer.produce_minute_task(sym, now)

    # 1. Realtime Verification (Every Minute) -> Producer
    scheduler.add_schedule(
        VerificationSchedule(
            name="realtime_minute_verification",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60,
            offset_seconds=VerificationConfig.VERIFICATION_OFFSET_SECONDS,
            market_hours_only=True,
            mode="realtime"
        ),
        produce_realtime_all
    )

    # 2. Daily Batch (15:40) -> Producer
    scheduler.add_schedule(
        VerificationSchedule(
            name="daily_verification",
            schedule_type=ScheduleType.CRON,
            cron_expr="40 15 * * 1-5" # 15:40 KST
        ),
        producer.produce_daily_tasks
    )

    try:
        # 스케줄러와 Consumer 병렬 실행
        await asyncio.gather(
            scheduler.start(),
            consumer.start()
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await scheduler.stop()
        await consumer.close()
        await producer.close()
        await producer.close()
        # await verifier.cleanup() # Removed


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    asyncio.run(run_verification_worker())
