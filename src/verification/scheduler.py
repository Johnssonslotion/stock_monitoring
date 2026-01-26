"""
Verification Scheduler
======================
RFC-008 Appendix E.2 구현

검증 작업의 스케줄링을 관리한다.
- Cron 기반 배치 검증 (장 마감 후)
- Interval 기반 실시간 검증 (장 중)
"""
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Dict, Any
from datetime import datetime, time
import asyncio
import logging
import pytz # Assuming pytz is available or use zoneinfo
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """스케줄 유형"""
    CRON = "cron"           # Cron 표현식
    INTERVAL = "interval"   # 주기적 실행
    MARKET_EVENT = "event"  # 장 이벤트 기반


@dataclass
class VerificationSchedule:
    """
    검증 작업 스케줄 정의

    Attributes:
        name: 스케줄 이름 (고유)
        schedule_type: 스케줄 유형
        cron_expr: Cron 표현식 (schedule_type == CRON)
        interval_seconds: 실행 간격 초 (schedule_type == INTERVAL)
        offset_seconds: 매 분/시간의 오프셋 초 (예: 5 = 매 분 +5초에 실행)
        market_event: 장 이벤트 (schedule_type == MARKET_EVENT)
        enabled: 활성화 여부
        market_hours_only: 장 중에만 실행 여부
        mode: 검증 모드 (batch/realtime)
    """
    name: str
    schedule_type: ScheduleType

    # Cron 설정
    cron_expr: Optional[str] = None  # "40 15 * * 1-5"

    # Interval 설정
    interval_seconds: Optional[int] = None
    offset_seconds: int = 0

    # Market Event 설정
    market_event: Optional[str] = None  # "MARKET_CLOSE", "MARKET_OPEN"
    offset_minutes: int = 0

    # 공통
    enabled: bool = True
    timezone: str = "Asia/Seoul"
    market_hours_only: bool = False
    mode: str = "batch"  # batch / realtime


class MarketSchedule:
    """한국 주식 시장 스케줄"""

    # 장 시간 (KST)
    MARKET_OPEN = time(9, 0)      # 09:00
    MARKET_CLOSE = time(15, 30)   # 15:30
    PRE_MARKET = time(8, 30)      # 08:30 (동시호가 시작)
    POST_MARKET = time(16, 0)     # 16:00 (시간외 종료)

    @classmethod
    def is_market_hours(cls, dt: Optional[datetime] = None) -> bool:
        """현재 장 중인지 확인 (KST 기준)"""
        kst = ZoneInfo("Asia/Seoul")
        if dt is None:
            dt = datetime.now(kst)
        elif dt.tzinfo is None:
            # If naive, assume it's naive local time (which is UTC in container)
            # Convert UTC naive to KST
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(kst)
        else:
             dt = dt.astimezone(kst)

        current_time = dt.time()

        # 주말 체크
        if dt.weekday() >= 5:
            return False

        return cls.MARKET_OPEN <= current_time <= cls.MARKET_CLOSE

    @classmethod
    def is_trading_day(cls, dt: Optional[datetime] = None) -> bool:
        """거래일인지 확인 (휴장일 제외 - 간단 버전)"""
        if dt is None:
            dt = datetime.now()
        return dt.weekday() < 5  # 주말 제외

    @classmethod
    def next_market_open(cls, dt: Optional[datetime] = None) -> datetime:
        """다음 장 시작 시간 (KST)"""
        kst = ZoneInfo("Asia/Seoul")
        if dt is None:
            dt = datetime.now(kst)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(kst)
        else:
            dt = dt.astimezone(kst)

        # 오늘 장 시작 전이면 오늘
        if dt.time() < cls.MARKET_OPEN and dt.weekday() < 5:
            return dt.replace(
                hour=cls.MARKET_OPEN.hour,
                minute=cls.MARKET_OPEN.minute,
                second=0,
                microsecond=0
            )

        # 다음 거래일 찾기
        next_day = dt.replace(hour=cls.MARKET_OPEN.hour, minute=cls.MARKET_OPEN.minute, second=0, microsecond=0)
        while True:
            next_day = next_day.replace(day=next_day.day + 1)
            if next_day.weekday() < 5:
                return next_day


class BaseScheduler:
    """스케줄러 추상 인터페이스"""

    def __init__(self):
        self._jobs: Dict[str, Any] = {}
        self._running = False

    async def start(self) -> None:
        """스케줄러 시작"""
        self._running = True

    async def stop(self) -> None:
        """스케줄러 중지"""
        self._running = False

    def add_job(self, schedule: VerificationSchedule, func: Callable) -> str:
        """작업 추가, job_id 반환"""
        raise NotImplementedError

    def remove_job(self, job_id: str) -> bool:
        """작업 제거"""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False


class SimpleIntervalScheduler(BaseScheduler):
    """
    간단한 Interval 기반 스케줄러 (asyncio 사용)

    APScheduler 없이도 동작하는 경량 스케줄러.
    """

    def __init__(self):
        super().__init__()
        self._tasks: Dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        """스케줄러 시작"""
        await super().start()
        logger.info("SimpleIntervalScheduler started")

    async def stop(self) -> None:
        """스케줄러 중지 및 모든 작업 취소"""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        logger.info("SimpleIntervalScheduler stopped")

    def add_job(self, schedule: VerificationSchedule, func: Callable) -> str:
        """
        Interval 작업 추가

        Args:
            schedule: 스케줄 정의
            func: 실행할 async 함수

        Returns:
            job_id
        """
        if schedule.schedule_type != ScheduleType.INTERVAL:
            raise ValueError(f"Unsupported schedule type: {schedule.schedule_type}")

        job_id = schedule.name
        self._jobs[job_id] = {
            "schedule": schedule,
            "func": func
        }

        # 비동기 태스크 생성
        task = asyncio.create_task(
            self._run_interval_job(schedule, func)
        )
        self._tasks[job_id] = task

        logger.info(f"Job added: {job_id} (interval={schedule.interval_seconds}s, offset={schedule.offset_seconds}s)")
        return job_id

    async def _run_interval_job(self, schedule: VerificationSchedule, func: Callable):
        """Interval 작업 실행 루프"""
        interval = schedule.interval_seconds or 60
        offset = schedule.offset_seconds

        while self._running:
            try:
                # 다음 실행 시점 계산 (offset 적용)
                now = datetime.now()
                if interval >= 60:  # 분 단위
                    # 다음 분의 offset초에 실행
                    next_minute = now.replace(second=0, microsecond=0)
                    if now.second >= offset:
                        next_minute = next_minute.replace(minute=next_minute.minute + 1)
                    next_run = next_minute.replace(second=offset)
                else:
                    next_run = now

                wait_time = (next_run - now).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                # 장 시간 체크
                if schedule.market_hours_only and not MarketSchedule.is_market_hours():
                    logger.debug(f"Job {schedule.name} skipped (outside market hours)")
                    await asyncio.sleep(interval)
                    continue

                # 실행
                logger.debug(f"Running job: {schedule.name}")
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()

                # 다음 interval까지 대기
                await asyncio.sleep(interval - offset if offset > 0 else interval)

            except asyncio.CancelledError:
                logger.info(f"Job {schedule.name} cancelled")
                break
            except Exception as e:
                logger.error(f"Job {schedule.name} error: {e}")
                await asyncio.sleep(interval)


class CronScheduler(BaseScheduler):
    """
    Cron 기반 스케줄러

    시스템 crontab 또는 APScheduler 사용.
    간단한 구현을 위해 asyncio + 시간 체크 방식 사용.
    """

    def __init__(self):
        super().__init__()
        self._check_interval = 30  # 30초마다 체크

    async def start(self) -> None:
        """스케줄러 시작"""
        await super().start()
        asyncio.create_task(self._cron_loop())
        logger.info("CronScheduler started")

    async def _cron_loop(self):
        """Cron 표현식 체크 루프"""
        while self._running:
            now = datetime.now()

            for job_id, job_info in self._jobs.items():
                schedule = job_info["schedule"]
                func = job_info["func"]

                if self._should_run(schedule.cron_expr, now):
                    logger.info(f"Cron job triggered: {job_id}")
                    try:
                        if asyncio.iscoroutinefunction(func):
                            await func()
                        else:
                            func()
                    except Exception as e:
                        logger.error(f"Cron job {job_id} error: {e}")

            await asyncio.sleep(self._check_interval)

    def _should_run(self, cron_expr: str, now: datetime) -> bool:
        """
        Cron 표현식 매칭 (간단 버전)

        Format: "분 시 일 월 요일"
        예: "40 15 * * 1-5" = 월~금 15:40
        """
        if not cron_expr:
            return False

        parts = cron_expr.split()
        if len(parts) != 5:
            return False

        minute, hour, day, month, weekday = parts

        # 분 체크 (30초 윈도우 내)
        if minute != "*" and abs(now.minute - int(minute)) > 0:
            return False

        # 시 체크
        if hour != "*" and now.hour != int(hour):
            return False

        # 요일 체크
        if weekday != "*":
            if "-" in weekday:
                start, end = map(int, weekday.split("-"))
                if not (start <= now.weekday() + 1 <= end):
                    return False
            elif now.weekday() + 1 != int(weekday):
                return False

        # 초가 0~30 사이일 때만 트리거 (중복 방지)
        return now.second < self._check_interval

    def add_job(self, schedule: VerificationSchedule, func: Callable) -> str:
        """Cron 작업 추가"""
        job_id = schedule.name
        self._jobs[job_id] = {
            "schedule": schedule,
            "func": func
        }
        logger.info(f"Cron job added: {job_id} ({schedule.cron_expr})")
        return job_id


class VerificationSchedulerManager:
    """
    검증 스케줄러 통합 관리자

    Interval과 Cron 스케줄러를 통합 관리.
    """

    def __init__(self):
        self.interval_scheduler = SimpleIntervalScheduler()
        self.cron_scheduler = CronScheduler()
        self._schedules: Dict[str, VerificationSchedule] = {}

    async def start(self):
        """모든 스케줄러 시작"""
        await asyncio.gather(
            self.interval_scheduler.start(),
            self.cron_scheduler.start()
        )
        logger.info("VerificationSchedulerManager started")

    async def stop(self):
        """모든 스케줄러 중지"""
        await asyncio.gather(
            self.interval_scheduler.stop(),
            self.cron_scheduler.stop()
        )
        logger.info("VerificationSchedulerManager stopped")

    def add_schedule(self, schedule: VerificationSchedule, func: Callable) -> str:
        """
        스케줄 추가

        schedule_type에 따라 적절한 스케줄러에 등록.
        """
        self._schedules[schedule.name] = schedule

        if schedule.schedule_type == ScheduleType.INTERVAL:
            return self.interval_scheduler.add_job(schedule, func)
        elif schedule.schedule_type == ScheduleType.CRON:
            return self.cron_scheduler.add_job(schedule, func)
        else:
            raise ValueError(f"Unsupported schedule type: {schedule.schedule_type}")

    def remove_schedule(self, name: str) -> bool:
        """스케줄 제거"""
        if name not in self._schedules:
            return False

        schedule = self._schedules[name]
        del self._schedules[name]

        if schedule.schedule_type == ScheduleType.INTERVAL:
            return self.interval_scheduler.remove_job(name)
        else:
            return self.cron_scheduler.remove_job(name)

    def get_schedule(self, name: str) -> Optional[VerificationSchedule]:
        """스케줄 조회"""
        return self._schedules.get(name)

    def list_schedules(self) -> Dict[str, VerificationSchedule]:
        """모든 스케줄 조회"""
        return self._schedules.copy()


# 기본 스케줄 설정 (RFC-008 Appendix E)
DEFAULT_SCHEDULES = [
    # 장 마감 후 전체 검증 (15:40)
    VerificationSchedule(
        name="daily_full_verification",
        schedule_type=ScheduleType.CRON,
        cron_expr="40 15 * * 1-5",
        mode="batch"
    ),

    # 장 중 1분 간격 실시간 검증 (매 분 +5초)
    VerificationSchedule(
        name="realtime_minute_verification",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=60,
        offset_seconds=5,
        market_hours_only=True,
        mode="realtime"
    ),

    # Pre-flight 체크 (08:30)
    VerificationSchedule(
        name="preflight_check",
        schedule_type=ScheduleType.CRON,
        cron_expr="30 8 * * 1-5",
        mode="batch"
    ),
]
