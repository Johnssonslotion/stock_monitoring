"""
Verification Worker (Producer/Consumer)
=======================================
RFC-008 Appendix E.4 구현

Redis Queue 기반 비동기 검증 작업 처리.
- Producer: 검증 작업 생성 → Redis Queue
- Consumer: Redis Queue → API 호출 → DB 저장
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
import aiohttp

from src.api_gateway.rate_limiter import gatekeeper
from src.verification.api_registry import (
    api_registry, APITarget, APIProvider, APIEndpointType
)

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


# === API Clients ===

class KiwoomAPIClient:
    """Kiwoom REST API 클라이언트"""

    BASE_URL = "https://api.kiwoom.com"
    TOKEN_URL = f"{BASE_URL}/oauth2/token"

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def get_token(self, session: aiohttp.ClientSession) -> str:
        """토큰 발급 (캐싱)"""
        # 만료 1시간 전 갱신
        if self._token and self._token_expires:
            if datetime.now() < self._token_expires - timedelta(hours=1):
                return self._token

        payload = {
            "grant_type": "client_credentials",
            "appkey": os.getenv("KIWOOM_APP_KEY"),
            "secretkey": os.getenv("KIWOOM_APP_SECRET")
        }
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }

        async with session.post(self.TOKEN_URL, json=payload, headers=headers) as resp:
            data = await resp.json()
            if data.get("return_code") == 0:
                self._token = data.get("token")
                # expires_dt: "20260121120000" 형식
                expires_str = data.get("expires_dt", "")
                if expires_str:
                    self._token_expires = datetime.strptime(expires_str, "%Y%m%d%H%M%S")
                logger.info(f"Kiwoom token acquired: {self._token[:15]}...")
                return self._token
            else:
                raise Exception(f"Kiwoom token error: {data}")

    async def fetch_minute_candle(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        target: APITarget
    ) -> Optional[Dict[str, Any]]:
        """분봉 데이터 조회"""
        token = await self.get_token(session)

        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": target.tr_id,
            "User-Agent": "Mozilla/5.0"
        }
        body = {
            "stk_cd": symbol,
            "chart_type": "1"
        }

        url = f"{self.BASE_URL}{target.path}"
        async with session.post(url, json=body, headers=headers, timeout=target.timeout_sec) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("return_code") == 0:
                    data_key = target.response_mapping.get("data_key", "stk_min_pole_chart_qry")
                    return data.get(data_key, [])
            elif resp.status == 429:
                logger.warning(f"Kiwoom rate limit exceeded for {symbol}")
            else:
                logger.error(f"Kiwoom API error: {resp.status}")
            return None


class KISAPIClient:
    """KIS REST API 클라이언트"""

    BASE_URL = "https://openapi.koreainvestment.com:9443"
    TOKEN_URL = f"{BASE_URL}/oauth2/tokenP"

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def get_token(self, session: aiohttp.ClientSession) -> str:
        """토큰 발급 (캐싱)"""
        if self._token and self._token_expires:
            if datetime.now() < self._token_expires - timedelta(hours=1):
                return self._token

        payload = {
            "grant_type": "client_credentials",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET")
        }

        async with session.post(self.TOKEN_URL, json=payload) as resp:
            data = await resp.json()
            self._token = data.get("access_token")
            expires_in = data.get("expires_in", 86400)
            self._token_expires = datetime.now() + timedelta(seconds=expires_in)
            logger.info(f"KIS token acquired: {self._token[:15]}...")
            return self._token

    async def fetch_minute_candle(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        target: APITarget
    ) -> Optional[Dict[str, Any]]:
        """분봉 데이터 조회"""
        token = await self.get_token(session)

        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {token}",
            "appkey": os.getenv("KIS_APP_KEY"),
            "appsecret": os.getenv("KIS_APP_SECRET"),
            "tr_id": target.tr_id
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
            "FID_INPUT_HOUR_1": "",
            "FID_PW_DATA_INCU_YN": "Y"
        }

        url = f"{self.BASE_URL}{target.path}"
        async with session.get(url, headers=headers, params=params, timeout=target.timeout_sec) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("output2", [])
            else:
                logger.error(f"KIS API error: {resp.status}")
            return None


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
    검증 작업 소비자 (Redis Queue → API → DB)

    Queue에서 작업을 가져와 듀얼 API 검증 수행 후 결과 저장.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/1")
        self.redis: Optional[redis.Redis] = None
        self.kiwoom_client = KiwoomAPIClient()
        self.kis_client = KISAPIClient()
        self._running = False
        self._results: List[VerificationResult] = []

    async def connect(self):
        """Redis 연결"""
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            await gatekeeper.connect()
            logger.info(f"Consumer connected to Redis: {self.redis_url}")

    async def close(self):
        """연결 종료"""
        self._running = False
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def start(self):
        """소비 루프 시작"""
        await self.connect()
        self._running = True
        logger.info("Consumer started")
        await self._consume_loop()

    async def stop(self):
        """소비 루프 중지"""
        self._running = False
        logger.info("Consumer stopping...")

    async def _consume_loop(self):
        """메인 소비 루프"""
        async with aiohttp.ClientSession() as session:
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
                    result = await self._process_task(session, task)
                    self._results.append(result)

                    if result.status == VerificationStatus.NEEDS_RECOVERY:
                        logger.warning(f"Recovery needed: {result.symbol}, delta={result.delta_pct:.2%}")

                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    # Dead Letter Queue로 이동
                    if raw_task:
                        await self.redis.lpush(VerificationConfig.DLQ_KEY, raw_task)

    async def _process_task(
        self,
        session: aiohttp.ClientSession,
        task: VerificationTask
    ) -> VerificationResult:
        """
        작업 처리: Rate Limit → API 호출 → 교차 검증

        Args:
            session: aiohttp 세션
            task: 검증 작업

        Returns:
            VerificationResult
        """
        symbol = task.symbol

        # 듀얼 API 타겟 조회
        targets = api_registry.get_all_targets(APIEndpointType.MINUTE_CANDLE)
        api_results = {}

        for target in targets:
            # Rate Limit 획득
            acquired = await gatekeeper.wait_acquire(target.rate_limit_key, timeout=5.0)
            if not acquired:
                logger.warning(f"Rate limit timeout for {target.provider.value}")
                continue

            # API 호출
            try:
                if target.provider == APIProvider.KIWOOM:
                    data = await self.kiwoom_client.fetch_minute_candle(session, symbol, target)
                else:
                    data = await self.kis_client.fetch_minute_candle(session, symbol, target)

                if data:
                    # 거래량 합계 계산
                    volume_key = target.response_mapping.get("volume", "trde_qty")
                    total_volume = sum(
                        int(item.get(volume_key, 0)) for item in data if isinstance(item, dict)
                    )
                    api_results[target.provider.value] = total_volume
                    logger.debug(f"{target.provider.value} volume for {symbol}: {total_volume}")

            except Exception as e:
                logger.error(f"API call failed: {target.provider.value} - {e}")

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
