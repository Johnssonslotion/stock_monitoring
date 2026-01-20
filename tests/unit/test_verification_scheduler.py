"""
Verification Scheduler 단위 테스트
==================================
RFC-008 Appendix F TC-F010~F013
"""
import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

from src.verification.scheduler import (
    VerificationSchedule,
    ScheduleType,
    MarketSchedule,
    SimpleIntervalScheduler,
    CronScheduler,
    VerificationSchedulerManager,
    DEFAULT_SCHEDULES
)


class TestVerificationSchedule:
    """VerificationSchedule 데이터클래스 테스트"""

    # TC-F010: Cron 스케줄 생성
    def test_cron_schedule_creation(self):
        """Cron 타입 스케줄 생성"""
        schedule = VerificationSchedule(
            name="daily_verification",
            schedule_type=ScheduleType.CRON,
            cron_expr="40 15 * * 1-5"
        )
        assert schedule.schedule_type == ScheduleType.CRON
        assert schedule.cron_expr == "40 15 * * 1-5"
        assert schedule.enabled is True
        assert schedule.mode == "batch"

    # TC-F011: Interval 스케줄 생성
    def test_interval_schedule_creation(self):
        """Interval 타입 스케줄 생성"""
        schedule = VerificationSchedule(
            name="intraday_check",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60,
            offset_seconds=5,
            market_hours_only=True
        )
        assert schedule.interval_seconds == 60
        assert schedule.offset_seconds == 5
        assert schedule.market_hours_only is True

    # TC-F012: Market Event 스케줄 생성
    def test_market_event_schedule_creation(self):
        """Market Event 타입 스케줄 생성"""
        schedule = VerificationSchedule(
            name="post_market",
            schedule_type=ScheduleType.MARKET_EVENT,
            market_event="MARKET_CLOSE",
            offset_minutes=10
        )
        assert schedule.market_event == "MARKET_CLOSE"
        assert schedule.offset_minutes == 10

    def test_default_schedules_defined(self):
        """기본 스케줄 정의 확인"""
        assert len(DEFAULT_SCHEDULES) >= 2

        # 장 마감 후 배치 검증
        daily = next((s for s in DEFAULT_SCHEDULES if s.name == "daily_full_verification"), None)
        assert daily is not None
        assert daily.cron_expr == "40 15 * * 1-5"

        # 실시간 검증
        realtime = next((s for s in DEFAULT_SCHEDULES if s.name == "realtime_minute_verification"), None)
        assert realtime is not None
        assert realtime.interval_seconds == 60
        assert realtime.offset_seconds == 5


class TestMarketSchedule:
    """MarketSchedule 테스트"""

    def test_market_hours_during_session(self):
        """장 중 시간 확인"""
        # 10:00 KST (월요일)
        dt = datetime(2026, 1, 20, 10, 0, 0)  # 월요일
        assert MarketSchedule.is_market_hours(dt) is True

        # 09:00 (장 시작)
        dt = datetime(2026, 1, 20, 9, 0, 0)
        assert MarketSchedule.is_market_hours(dt) is True

        # 15:30 (장 마감)
        dt = datetime(2026, 1, 20, 15, 30, 0)
        assert MarketSchedule.is_market_hours(dt) is True

    def test_market_hours_outside_session(self):
        """장외 시간 확인"""
        # 08:30 (프리마켓)
        dt = datetime(2026, 1, 20, 8, 30, 0)
        assert MarketSchedule.is_market_hours(dt) is False

        # 16:00 (장 마감 후)
        dt = datetime(2026, 1, 20, 16, 0, 0)
        assert MarketSchedule.is_market_hours(dt) is False

    def test_weekend_not_trading(self):
        """주말은 거래일 아님"""
        # 토요일
        dt = datetime(2026, 1, 24, 10, 0, 0)
        assert MarketSchedule.is_market_hours(dt) is False
        assert MarketSchedule.is_trading_day(dt) is False

        # 일요일
        dt = datetime(2026, 1, 25, 10, 0, 0)
        assert MarketSchedule.is_market_hours(dt) is False


class TestSimpleIntervalScheduler:
    """SimpleIntervalScheduler 테스트"""

    @pytest.fixture
    def scheduler(self):
        return SimpleIntervalScheduler()

    # TC-F013: 스케줄러 작업 추가
    @pytest.mark.asyncio
    async def test_scheduler_add_job(self, scheduler):
        """Interval 스케줄러에 작업 추가"""
        schedule = VerificationSchedule(
            name="test_job",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60
        )

        mock_func = AsyncMock()
        job_id = scheduler.add_job(schedule, mock_func)

        assert job_id == "test_job"
        assert "test_job" in scheduler._jobs
        assert "test_job" in scheduler._tasks

    @pytest.mark.asyncio
    async def test_scheduler_remove_job(self, scheduler):
        """작업 제거"""
        schedule = VerificationSchedule(
            name="test_job",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60
        )
        scheduler.add_job(schedule, AsyncMock())

        result = scheduler.remove_job("test_job")
        assert result is True
        assert "test_job" not in scheduler._jobs

    def test_invalid_schedule_type_raises(self, scheduler):
        """잘못된 스케줄 타입은 예외 발생"""
        schedule = VerificationSchedule(
            name="cron_job",
            schedule_type=ScheduleType.CRON,
            cron_expr="0 * * * *"
        )

        with pytest.raises(ValueError):
            scheduler.add_job(schedule, AsyncMock())


class TestCronScheduler:
    """CronScheduler 테스트"""

    @pytest.fixture
    def scheduler(self):
        return CronScheduler()

    def test_cron_pattern_matching_exact(self, scheduler):
        """Cron 표현식 정확한 매칭"""
        # "40 15 * * 1-5" = 월~금 15:40
        cron_expr = "40 15 * * 1-5"

        # 월요일 15:40:05
        dt = datetime(2026, 1, 20, 15, 40, 5)
        assert scheduler._should_run(cron_expr, dt) is True

        # 월요일 15:39
        dt = datetime(2026, 1, 20, 15, 39, 0)
        assert scheduler._should_run(cron_expr, dt) is False

        # 월요일 16:40
        dt = datetime(2026, 1, 20, 16, 40, 0)
        assert scheduler._should_run(cron_expr, dt) is False

    def test_cron_weekday_range(self, scheduler):
        """Cron 요일 범위 매칭"""
        cron_expr = "0 9 * * 1-5"  # 월~금 09:00

        # 일요일 (2026-01-25)
        dt = datetime(2026, 1, 25, 9, 0, 5)  # 일요일
        assert scheduler._should_run(cron_expr, dt) is False

        # 월요일 (2026-01-20)
        dt = datetime(2026, 1, 20, 9, 0, 5)  # 월요일
        assert scheduler._should_run(cron_expr, dt) is True


class TestVerificationSchedulerManager:
    """VerificationSchedulerManager 통합 테스트"""

    @pytest.fixture
    def manager(self):
        return VerificationSchedulerManager()

    def test_add_cron_schedule(self, manager):
        """Cron 스케줄 추가 (동기 테스트 가능)"""
        schedule = VerificationSchedule(
            name="cron_test",
            schedule_type=ScheduleType.CRON,
            cron_expr="0 10 * * *"
        )

        job_id = manager.add_schedule(schedule, AsyncMock())
        assert job_id == "cron_test"
        assert manager.get_schedule("cron_test") is not None

    def test_cron_schedule_remove(self, manager):
        """Cron 스케줄 제거"""
        schedule = VerificationSchedule(
            name="to_remove_cron",
            schedule_type=ScheduleType.CRON,
            cron_expr="0 * * * *"
        )
        manager.add_schedule(schedule, AsyncMock())

        result = manager.remove_schedule("to_remove_cron")
        assert result is True
        assert manager.get_schedule("to_remove_cron") is None

    def test_list_cron_schedules(self, manager):
        """Cron 스케줄 목록 조회"""
        manager.add_schedule(
            VerificationSchedule(
                name="cron1",
                schedule_type=ScheduleType.CRON,
                cron_expr="0 9 * * *"
            ),
            AsyncMock()
        )
        manager.add_schedule(
            VerificationSchedule(
                name="cron2",
                schedule_type=ScheduleType.CRON,
                cron_expr="0 15 * * *"
            ),
            AsyncMock()
        )

        schedules = manager.list_schedules()
        assert len(schedules) == 2
        assert "cron1" in schedules
        assert "cron2" in schedules

    # Interval 테스트는 asyncio 환경 필요 (별도 통합 테스트에서 수행)
    @pytest.mark.skip(reason="Requires running event loop - tested in integration")
    def test_add_interval_schedule(self, manager):
        """Interval 스케줄 추가 (asyncio 필요)"""
        pass
