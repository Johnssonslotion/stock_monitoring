"""
Realtime Verifier
=================
RFC-008 Appendix H 구현

장 중 실시간 데이터 검증 및 즉시 복구 트리거.
- 매 분 +5초에 직전 1분 데이터 검증
- Tolerance 2% 기반 Gap 감지
- 우선순위 큐를 통한 즉시 복구
"""
import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import aiohttp
import redis.asyncio as redis

from src.api_gateway.rate_limiter import gatekeeper
from src.verification.api_registry import (
    api_registry, APIProvider, APIEndpointType
)
from src.verification.scheduler import (
    VerificationSchedulerManager,
    VerificationSchedule,
    ScheduleType,
    MarketSchedule
)
from src.verification.worker import (
    KiwoomAPIClient,
    VerificationProducer,
    VerificationConfig,
    VerificationResult,
    VerificationStatus,
    ConfidenceLevel
)

logger = logging.getLogger(__name__)


@dataclass
class RealtimeConfig:
    """실시간 검증 설정"""
    # Tolerance (2% for realtime)
    volume_tolerance_pct: float = 0.02

    # 최소 거래량 (미만 시 스킵)
    min_volume_threshold: int = 100

    # 복구 전 대기 시간 (지연 체결 대응)
    recovery_delay_sec: float = 3.0

    # 최대 복구 재시도
    max_recovery_retries: int = 2

    # 한 번에 검증할 최대 종목 수
    max_symbols_per_run: int = 10

    # 우선 검증 종목 (대형주)
    priority_symbols: List[str] = None

    def __post_init__(self):
        if self.priority_symbols is None:
            self.priority_symbols = [
                "005930",  # 삼성전자
                "000660",  # SK하이닉스
                "035420",  # NAVER
                "035720",  # 카카오
                "051910",  # LG화학
                "006400",  # 삼성SDI
                "207940",  # 삼성바이오로직스
                "005380",  # 현대차
                "068270",  # 셀트리온
                "028260",  # 삼성물산
            ]


class RealtimeVerifier:
    """
    장 중 실시간 검증 워커

    매 분 +5초에 직전 1분 데이터를 검증하고,
    Gap 감지 시 즉시 복구 작업을 트리거한다.
    """

    def __init__(
        self,
        config: Optional[RealtimeConfig] = None,
        redis_url: Optional[str] = None,
        db_url: Optional[str] = None
    ):
        self.config = config or RealtimeConfig()
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/1")
        self.db_url = db_url or os.getenv("TIMESCALE_URL")

        self.redis: Optional[redis.Redis] = None
        self.kiwoom_client = KiwoomAPIClient()
        self.producer = VerificationProducer(redis_url)

        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._stats = {
            "verified": 0,
            "passed": 0,
            "gaps_detected": 0,
            "skipped": 0
        }

    async def initialize(self):
        """초기화"""
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        self._session = aiohttp.ClientSession()
        await gatekeeper.connect()
        await self.producer.connect()
        logger.info("RealtimeVerifier initialized")

    async def cleanup(self):
        """정리"""
        self._running = False
        if self._session:
            await self._session.close()
        if self.redis:
            await self.redis.close()
        await self.producer.close()
        logger.info("RealtimeVerifier cleaned up")

    async def verify_last_minute(self, symbol: str) -> VerificationResult:
        """
        직전 1분 데이터 검증

        Args:
            symbol: 종목 코드

        Returns:
            VerificationResult
        """
        # 검증 대상 시간 (직전 분)
        now = datetime.now()
        target_minute = now.replace(second=0, microsecond=0) - timedelta(minutes=1)

        # 1. DB에서 틱 거래량 합계 조회
        db_volume = await self._get_tick_volume_from_db(symbol, target_minute)

        # 저유동성 스킵
        if db_volume is not None and db_volume < self.config.min_volume_threshold:
            logger.debug(f"Skip low volume: {symbol} @ {target_minute} (vol={db_volume})")
            self._stats["skipped"] += 1
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.SKIPPED,
                confidence=ConfidenceLevel.SKIP,
                db_volume=db_volume,
                message=f"Low volume: {db_volume} < {self.config.min_volume_threshold}"
            )

        # 2. Rate Limit 획득 후 분봉 API 조회
        target = api_registry.get_target(APIEndpointType.MINUTE_CANDLE, APIProvider.KIWOOM)
        if not target:
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.ERROR,
                confidence=ConfidenceLevel.SKIP,
                message="No API target available"
            )

        acquired = await gatekeeper.wait_acquire(target.rate_limit_key, timeout=2.0)
        if not acquired:
            self._stats["skipped"] += 1
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.SKIPPED,
                confidence=ConfidenceLevel.SKIP,
                message="Rate limit timeout"
            )

        # API 호출
        api_data = await self.kiwoom_client.fetch_minute_candle(
            self._session, symbol, target
        )

        if not api_data:
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.ERROR,
                confidence=ConfidenceLevel.SKIP,
                message="API returned no data"
            )

        # 해당 분봉 찾기
        api_volume = self._extract_minute_volume(api_data, target_minute)

        if api_volume is None:
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.SKIPPED,
                confidence=ConfidenceLevel.SKIP,
                message="Target minute not found in API response"
            )

        # 3. Tolerance 기반 비교
        self._stats["verified"] += 1

        if db_volume is None:
            db_volume = 0

        delta_pct = abs(api_volume - db_volume) / max(api_volume, 1)

        if delta_pct <= self.config.volume_tolerance_pct:
            self._stats["passed"] += 1
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.PASS,
                confidence=ConfidenceLevel.HIGH,
                kiwoom_volume=api_volume,
                db_volume=db_volume,
                delta_pct=delta_pct,
                message="Realtime verification passed"
            )
        else:
            # Gap 감지 → 복구 트리거
            self._stats["gaps_detected"] += 1
            gap = api_volume - db_volume

            await self._trigger_recovery(symbol, target_minute, gap)

            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.NEEDS_RECOVERY,
                confidence=ConfidenceLevel.MEDIUM,
                kiwoom_volume=api_volume,
                db_volume=db_volume,
                delta_pct=delta_pct,
                message=f"Gap detected: {gap} ticks ({delta_pct:.2%})"
            )

    async def _get_tick_volume_from_db(
        self,
        symbol: str,
        minute: datetime
    ) -> Optional[int]:
        """
        DB에서 틱 거래량 합계 조회

        Args:
            symbol: 종목 코드
            minute: 조회 대상 분

        Returns:
            거래량 합계 또는 None
        """
        # TODO: 실제 DB 연결 구현
        # 현재는 Redis에 캐시된 값 조회 시도
        cache_key = f"tick_volume:{symbol}:{minute.strftime('%Y%m%d%H%M')}"
        cached = await self.redis.get(cache_key)
        if cached:
            return int(cached)

        # DB 조회 (TimescaleDB/DuckDB)
        # query = """
        #     SELECT COALESCE(SUM(volume), 0) as total_volume
        #     FROM market_ticks
        #     WHERE symbol = $1
        #       AND timestamp >= $2
        #       AND timestamp < $3
        # """
        # 임시: None 반환 (실제 구현 필요)
        logger.debug(f"DB volume query for {symbol} @ {minute} - not implemented")
        return None

    def _extract_minute_volume(
        self,
        api_data: List[Dict[str, Any]],
        target_minute: datetime
    ) -> Optional[int]:
        """
        API 응답에서 특정 분봉의 거래량 추출

        Args:
            api_data: API 응답 데이터
            target_minute: 대상 분

        Returns:
            거래량 또는 None
        """
        target_str = target_minute.strftime("%Y%m%d%H%M")

        for item in api_data:
            if not isinstance(item, dict):
                continue

            # Kiwoom 분봉 응답의 시간 필드
            dt = item.get("dt", item.get("stck_bsop_date", ""))

            # 형식: "202601201000" (YYYYMMDDHHMM)
            if dt.startswith(target_str[:12]):  # 분까지 매칭
                volume = item.get("trde_qty", item.get("cntg_vol", 0))
                return int(volume) if volume else 0

        return None

    async def _trigger_recovery(self, symbol: str, minute: datetime, gap: int):
        """
        복구 트리거

        Args:
            symbol: 종목 코드
            minute: 대상 분
            gap: 거래량 Gap
        """
        # 복구 전 대기 (지연 체결 대응)
        if self.config.recovery_delay_sec > 0:
            await asyncio.sleep(self.config.recovery_delay_sec)

        # 우선순위 큐에 복구 작업 추가
        await self.producer.produce_recovery_task(symbol, minute, gap)

        logger.warning(f"⚠️ Recovery triggered: {symbol} @ {minute}, gap={gap}")

    async def run_verification_cycle(self) -> List[VerificationResult]:
        """
        검증 사이클 실행 (우선순위 종목)

        Returns:
            검증 결과 리스트
        """
        if not MarketSchedule.is_market_hours():
            logger.debug("Outside market hours, skipping verification")
            return []

        symbols = self.config.priority_symbols[:self.config.max_symbols_per_run]
        results = []

        for symbol in symbols:
            try:
                result = await self.verify_last_minute(symbol)
                results.append(result)

                # 짧은 대기 (API 부하 분산)
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Verification error for {symbol}: {e}")
                results.append(VerificationResult(
                    symbol=symbol,
                    minute=None,
                    status=VerificationStatus.ERROR,
                    confidence=ConfidenceLevel.SKIP,
                    message=str(e)
                ))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        return {
            **self._stats,
            "pass_rate": (
                self._stats["passed"] / self._stats["verified"]
                if self._stats["verified"] > 0 else 0
            )
        }

    def reset_stats(self):
        """통계 초기화"""
        self._stats = {
            "verified": 0,
            "passed": 0,
            "gaps_detected": 0,
            "skipped": 0
        }


async def run_realtime_verifier():
    """
    실시간 검증기 실행

    Usage:
        python -m src.verification.realtime_verifier
    """
    verifier = RealtimeVerifier()
    scheduler = VerificationSchedulerManager()

    await verifier.initialize()

    # 실시간 검증 스케줄 등록 (매 분 +5초)
    scheduler.add_schedule(
        VerificationSchedule(
            name="realtime_minute_verification",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60,
            offset_seconds=5,
            market_hours_only=True,
            mode="realtime"
        ),
        verifier.run_verification_cycle
    )

    try:
        logger.info("Starting realtime verifier...")
        await scheduler.start()

        # 무한 대기
        while True:
            await asyncio.sleep(60)

            # 주기적 통계 출력
            stats = verifier.get_stats()
            logger.info(f"📊 Realtime stats: {stats}")

    except KeyboardInterrupt:
        logger.info("Shutting down realtime verifier...")
    finally:
        await scheduler.stop()
        await verifier.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    asyncio.run(run_realtime_verifier())
