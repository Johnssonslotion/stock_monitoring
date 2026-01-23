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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis

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
    message: str = ""
    verified_at: str = ""

    def __post_init__(self):
        if not self.verified_at:
            self.verified_at = datetime.now().isoformat()


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
        """검증 대상 종목 조회"""
        if self._target_symbols:
            return self._target_symbols

        # DB에서 활성 종목 조회 (간단 버전: 기본 종목)
        return [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "035720",  # 카카오
            "051910",  # LG화학
        ]

    async def produce_daily_tasks(self):
        """장 마감 후 전체 검증 작업 생성"""
        await self.connect()

        symbols = await self.get_target_symbols()
        today = datetime.now().strftime("%Y%m%d")
        count = 0

        for symbol in symbols:
            task = VerificationTask(
                task_type="full_verification",
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
            task_type="minute_verification",
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

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/1")
        self.redis: Optional[redis.Redis] = None
        self.hub_client: Optional[APIHubClient] = None
        self._running = False
        self._results: List[VerificationResult] = []

    async def connect(self):
        """Redis 및 API Hub Client 연결"""
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Consumer connected to Redis: {self.redis_url}")
        
        if not self.hub_client:
            self.hub_client = APIHubClient()
            logger.info("API Hub Client initialized")

    async def close(self):
        """연결 종료"""
        self._running = False
        if self.redis:
            await self.redis.close()
            self.redis = None
        if self.hub_client:
            await self.hub_client.close()
            self.hub_client = None

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
                
                if task.task_type == "recovery":
                    result = await self._handle_recovery_task(task)
                else:
                    result = await self._process_task(task)
                
                self._results.append(result)

                if result.status == VerificationStatus.NEEDS_RECOVERY:
                    logger.warning(f"Recovery needed: {result.symbol}, delta={result.delta_pct:.2%}")

            except Exception as e:
                logger.error(f"Task failed: {e}")
                # Dead Letter Queue로 이동
                if raw_task:
                    await self.redis.lpush(VerificationConfig.DLQ_KEY, raw_task)

    async def _handle_recovery_task(self, task: VerificationTask) -> VerificationResult:
        """
        긴급 복구 작업 처리 (API Hub Queue 사용)
        
        ISSUE-041: KIS Tick Data 복구를 API Hub를 통해 처리
        """
        symbol = task.symbol
        # minute format: "2026-01-20T09:00:00"
        dt_min = datetime.fromisoformat(task.minute)
        # KIS API expects HHMMSS of the end of the window (approx)
        target_time_req = (dt_min + timedelta(minutes=1)).strftime("%H%M%S")
        
        logger.info(f"🛠️ Handling recovery task for {symbol} @ {dt_min.strftime('%H:%M')}")
        
        try:
            # API Hub를 통한 틱 데이터 조회 (TR Registry 사용)
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
                    # Filter and Save Ticks
                    recovered_count = await self._save_recovered_ticks(symbol, dt_min, items)
                    
                    return VerificationResult(
                        symbol=symbol,
                        minute=task.minute,
                        status=VerificationStatus.PASS,
                        confidence=ConfidenceLevel.HIGH,
                        message=f"Recovered {recovered_count} ticks via API Hub"
                    )
            elif result.get("status") == "RATE_LIMITED":
                logger.warning(f"[{symbol}] Rate limited by API Hub")
            else:
                logger.warning(f"[{symbol}] API Hub error: {result.get('reason')}")
        
        except Exception as e:
            logger.error(f"[{symbol}] Recovery failed: {e}")
        
        return VerificationResult(
            symbol=symbol,
            minute=task.minute,
            status=VerificationStatus.FAIL,
            confidence=ConfidenceLevel.LOW,
            message="Recovery failed (API Hub error)"
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
                rows.append((
                    tick_dt, symbol, "KIS_RECOVERY",
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
                provider="Kiwoom",
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

    producer = VerificationProducer()
    consumer = VerificationConsumer()
    scheduler = VerificationSchedulerManager()

    # 장 마감 후 배치 검증 스케줄
    scheduler.add_schedule(
        VerificationSchedule(
            name="daily_verification",
            schedule_type=ScheduleType.CRON,
            cron_expr="40 15 * * 1-5"
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


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    asyncio.run(run_verification_worker())
