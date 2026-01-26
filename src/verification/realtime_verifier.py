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
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import redis.asyncio as redis
import asyncpg

from src.api_gateway.hub.client import APIHubClient
from src.api_gateway.hub.tr_registry import UseCase, get_tr_id_for_use_case
from src.verification.scheduler import (
    VerificationSchedulerManager,
    VerificationSchedule,
    ScheduleType,
    MarketSchedule
)
from src.verification.worker import (
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
        self.api_hub_client = APIHubClient()
        self.producer = VerificationProducer(redis_url)
        self.db_pool: Optional[asyncpg.Pool] = None

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
        await self.producer.connect()
        
        # DB Pool initialization
        if self.db_url:
            self.db_pool = await asyncpg.create_pool(self.db_url)
            logger.info("RealtimeVerifier DB pool connected")
        
        logger.info("RealtimeVerifier initialized")

    async def cleanup(self):
        """정리"""
        self._running = False
        if self.redis:
            await self.redis.close()
        if self.db_pool:
            await self.db_pool.close()
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

        # 1. DB에서 로컬 캔들(OHLCV) 집계 조회
        local_candle = await self._get_local_candle_from_db(symbol, target_minute)

        # 거래량 추출 (없으면 0)
        db_volume = local_candle['volume'] if local_candle else 0

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

        # 2. Use API Hub Client to fetch minute candle data
        try:
            tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIWOOM)
            result = await self.api_hub_client.execute(
                provider="KIWOOM",
                tr_id=tr_id,
                params={
                    "symbol": symbol,
                    "time_unit": "1",  # 1-minute candles
                    "adj_price": "0",
                    "modified": "0",
                    "start_date": target_minute.strftime("%Y%m%d"),
                    "end_date": target_minute.strftime("%Y%m%d")
                },
                timeout=10.0
            )
            
            if not result or result.get("status") != "success":
                return VerificationResult(
                    symbol=symbol,
                    minute=target_minute.isoformat(),
                    status=VerificationStatus.ERROR,
                    confidence=ConfidenceLevel.SKIP,
                    message="API Hub returned error or no data"
                )
            
            api_data = result.get("data", [])
            
        except Exception as e:
            logger.error(f"API Hub error for {symbol}: {e}")
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.ERROR,
                confidence=ConfidenceLevel.SKIP,
                message=f"API Hub error: {str(e)}"
            )

        # 해당 분봉 찾기
        api_candle = self._extract_minute_candle(api_data, target_minute)

        if not api_candle:
            return VerificationResult(
                symbol=symbol,
                minute=target_minute.isoformat(),
                status=VerificationStatus.SKIPPED,
                confidence=ConfidenceLevel.SKIP,
                message="Target minute not found in API response"
            )

        api_volume = api_candle['volume']

        # 3. 상세 비교 (OHLC + Volume)
        self._stats["verified"] += 1

        if db_volume is None:
            db_volume = 0

        # Price Verify (Strict Match 1e-9)
        price_match = True
        mismatch_details = {}
        
        if local_candle and api_candle:
            for field in ['open', 'high', 'low', 'close']:
                local_val = local_candle.get(field, 0.0)
                api_val = api_candle.get(field, 0.0)
                if abs(local_val - api_val) > 1e-9:
                    price_match = False
                    mismatch_details[f"{field}_diff"] = local_val - api_val
                    mismatch_details[f"local_{field}"] = local_val
                    mismatch_details[f"api_{field}"] = api_val

        # Volume Verify (Tolerance 2%)
        delta_pct = abs(api_volume - db_volume) / max(api_volume, 1) if api_volume > 0 else 0.0
        
        # Determine Status
        status = VerificationStatus.PASS
        confidence = ConfidenceLevel.HIGH
        msg = "Realtime verification passed"

        if not price_match:
            status = VerificationStatus.NEEDS_RECOVERY
            confidence = ConfidenceLevel.MEDIUM
            msg = f"Price mismatch: {mismatch_details}"
            self._stats["gaps_detected"] += 1
            await self._trigger_recovery(symbol, target_minute, 0) # Gap 0 but price mismatch

        elif delta_pct > self.config.volume_tolerance_pct:
            status = VerificationStatus.NEEDS_RECOVERY
            confidence = ConfidenceLevel.MEDIUM
            msg = f"Volume Gap detected: {delta_pct:.2%}"
            self._stats["gaps_detected"] += 1
            gap = api_volume - db_volume
            await self._trigger_recovery(symbol, target_minute, gap)
        else:
            self._stats["passed"] += 1

        result = VerificationResult(
            symbol=symbol,
            minute=target_minute.isoformat(),
            status=status,
            confidence=confidence,
            kiwoom_volume=api_volume,
            db_volume=db_volume,
            delta_pct=delta_pct,
            price_match=price_match,
            details=mismatch_details if not price_match else None,
            message=msg
        )
        
        # 결과 DB 저장
        await self._save_verification_result(result)
        
        return result

    async def _get_local_candle_from_db(
        self,
        symbol: str,
        minute: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        DB(TimescaleDB)에서 로컬 캔들(OHLCV) 집계 조회
        """
        # 1. Redis 캐시 조회 (Archiver 등이 기록했을 경우) - TODO: OHLC 캐싱 전략 필요
        # 현재는 Volume만 캐싱하므로 일단 DB 직접 조회 (정확도 우선)
        
        if not self.db_pool:
            logger.warning("DB pool not initialized, cannot query candle")
            return None

        try:
            start_time = minute
            end_time = minute + timedelta(minutes=1)
            
            async with self.db_pool.acquire() as conn:
                # TimescaleDB first/last/max/min aggregation
                row = await conn.fetchrow("""
                    SELECT 
                        first(price, time) as open,
                        max(price) as high,
                        min(price) as low,
                        last(price, time) as close,
                        COALESCE(SUM(volume), 0) as volume
                    FROM market_ticks
                    WHERE symbol = $1
                      AND time >= $2
                      AND time < $3
                """, symbol, start_time, end_time)
                
                if row and row['open'] is not None:
                    return {
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    }
        except Exception as e:
            logger.error(f"Error querying DB candle for {symbol} @ {minute}: {e}")
            
        return None

    def _extract_minute_candle(
        self,
        api_data: List[Dict[str, Any]],
        target_minute: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        API 응답에서 특정 분봉의 OHLCV 추출
        """
        target_str = target_minute.strftime("%Y%m%d%H%M")

        for item in api_data:
            if not isinstance(item, dict):
                continue

            dt = item.get("dt", item.get("stck_bsop_date", ""))

            if dt.startswith(target_str[:12]):
                # Kiwoom fields: stck_oprc, stck_hgpr, stck_lwpr, stck_clpr, trde_qty (or cntg_vol)
                # Output keys might vary. Standardize here.
                return {
                    'open': float(abs(int(item.get('stck_oprc', 0)))),
                    'high': float(abs(int(item.get('stck_hgpr', 0)))),
                    'low': float(abs(int(item.get('stck_lwpr', 0)))),
                    'close': float(abs(int(item.get('stck_clpr', 0)))),
                    'volume': int(item.get("trde_qty", item.get("cntg_vol", 0)))
                }

        return None

    async def _save_verification_result(self, result: VerificationResult):
        """결과 DB 저장"""
        if not self.db_pool or not result.minute:
            return

        try:
            async with self.db_pool.acquire() as conn:
                # Use json.dumps for details dict
                details_json = json.dumps(result.details) if result.details else None
                
                await conn.execute("""
                    INSERT INTO market_verification_results
                    (time, symbol, local_vol, api_vol, price_match, details, status, 
                     kiwoom_vol, vol_delta_kiwoom)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                datetime.fromisoformat(result.minute),
                result.symbol,
                float(result.db_volume) if result.db_volume is not None else 0,
                float(result.kiwoom_volume) if result.kiwoom_volume is not None else 0,
                result.price_match,
                details_json,
                result.status.value,
                float(result.kiwoom_volume) if result.kiwoom_volume is not None else 0,
                result.delta_pct
                )
        except Exception as e:
            logger.error(f"Failed to save result: {e}")

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
