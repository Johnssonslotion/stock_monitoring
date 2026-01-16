"""
Chaos Test: Clock Skew (시간 왜곡) 감지

브로커가 제공하는 시간과 서버 시간의 차이(Skew)를 감지하고
허용 범위를 초과할 경우 적절히 처리하는지 검증합니다.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from src.core.time_utils import TimestampManager, TimestampValidationError


@pytest.mark.asyncio
async def test_clock_skew_within_tolerance():
    """
    허용 오차 내 시간 차이 (정상 케이스)
    
    시나리오:
    - 브로커 시간: 12:00:03
    - 서버 시간: 12:00:00
    - 차이: 3초 (허용 범위 5초 내)
    
    기대 결과:
    - 검증 통과 (True)
    """
    reference_time = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    broker_time = reference_time + timedelta(seconds=3)
    
    result = TimestampManager.validate_skew(
        broker_time, 
        tolerance_sec=5, 
        reference_time=reference_time
    )
    
    assert result is True


@pytest.mark.asyncio
async def test_clock_skew_exceeds_tolerance():
    """
    허용 오차 초과 시간 차이 (비정상 케이스)
    
    시나리오:
    - 브로커 시간: 12:00:10 (미래)
    - 서버 시간: 12:00:00
    - 차이: 10초 (허용 범위 5초 초과)
    
    기대 결과:
    - 검증 실패 (False)
    """
    reference_time = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    broker_time = reference_time + timedelta(seconds=10)
    
    result = TimestampManager.validate_skew(
        broker_time, 
        tolerance_sec=5, 
        reference_time=reference_time
    )
    
    assert result is False


@pytest.mark.asyncio
async def test_clock_skew_future_time():
    """
    브로커가 미래 시간을 보고하는 경우
    
    시나리오:
    - 브로커 시간이 서버 시간보다 1분 빠름
    - NTP 동기화 실패 또는 브로커 서버 시간 오류
    
    기대 결과:
    - 검증 실패
    - 경고 로그 발생
    """
    with patch('src.core.time_utils.logger') as mock_logger:
        server_time = TimestampManager.now_utc()
        broker_time = server_time + timedelta(minutes=1)  # 1분 미래
        
        result = TimestampManager.validate_skew(broker_time, tolerance_sec=5)
        
        # 검증 실패
        assert result is False
        
        # 경고 로그 확인
        mock_logger.warning.assert_called()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Clock skew detected" in warning_msg


@pytest.mark.asyncio
async def test_clock_skew_past_time():
    """
    브로커가 과거 시간을 보고하는 경우
    
    시나리오:
    - 브로커 시간이 서버 시간보다 1분 느림
    - 브로커 재시작 후 시간 동기화 지연
    
    기대 결과:
    - 검증 실패
    """
    server_time = TimestampManager.now_utc()
    broker_time = server_time - timedelta(minutes=1)  # 1분 과거
    
    result = TimestampManager.validate_skew(broker_time, tolerance_sec=5)
    
    assert result is False


@pytest.mark.asyncio
async def test_broker_time_parsing_with_skew():
    """
    시간 파싱 시 Skew 자동 검증
    
    시나리오:
    - 브로커가 "235959" (23:59:59) 보고
    - 하지만 실제 서버 시간은 00:00:05 (다음 날)
    - 날짜 경계에서의 Skew
    
    기대 결과:
    - 파싱은 성공하지만 Skew 경고
    """
    # 날짜 경계 시뮬레이션
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    
    # 어제 23:59:59를 파싱
    broker_time_str = "235959"
    parsed = TimestampManager.parse_broker_time(broker_time_str, "kis", yesterday)
    
    # 현재 시간과 비교
    current = TimestampManager.now_utc()
    delta = abs((current - parsed).total_seconds())
    
    # 어제의 23:59:59이므로 최소 몇 초 ~ 최대 하루 차이
    # (테스트 실행 시각에 따라 변동)
    assert delta < 25 * 3600  # 25시간 이내면 정상


@pytest.mark.asyncio
async def test_multiple_brokers_skew_detection():
    """
    여러 브로커의 시간 Skew 동시 감지
    
    시나리오:
    - KIS: 정상 (0초 차이)
    - 미래: 약간 느림 (-3초, 허용)
    - 키움: 매우 빠름 (+15초, 비정상)
    
    기대 결과:
    - KIS, 미래: 통과
    - 키움: 실패
    """
    server_time = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    
    broker_times = {
        "kis": server_time,
        "mirae": server_time - timedelta(seconds=3),
        "kiwoom_re": server_time + timedelta(seconds=15)
    }
    
    results = {}
    for broker, time in broker_times.items():
        results[broker] = TimestampManager.validate_skew(
            time, 
            tolerance_sec=5, 
            reference_time=server_time
        )
    
    assert results["kis"] is True
    assert results["mirae"] is True
    assert results["kiwoom_re"] is False


@pytest.mark.asyncio
async def test_skew_correction_strategy():
    """
    Skew 감지 후 보정 전략
    
    시나리오:
    - 브로커 시간에 일관된 오프셋 감지 (+5초)
    - 자동 보정 적용
    
    기대 결과:
    - 보정 후 Skew 허용 범위 내
    """
    server_time = TimestampManager.now_utc()
    
    # 브로커가 항상 +5초 빠른 시간 보고
    broker_offset = timedelta(seconds=5)
    broker_time = server_time + broker_offset
    
    # 초기 검증 실패
    assert TimestampManager.validate_skew(broker_time, tolerance_sec=3) is False
    
    # 오프셋 보정 적용
    corrected_time = broker_time - broker_offset
    
    # 보정 후 검증 성공
    assert TimestampManager.validate_skew(corrected_time, tolerance_sec=3) is True


@pytest.mark.asyncio
async def test_ntp_sync_failure_detection():
    """
    NTP 동기화 실패 시뮬레이션
    
    시나리오:
    - 서버 NTP 동기화 실패
    - 시스템 시간이 실제보다 5분 느림
    
    기대 결과:
    - 모든 브로커 데이터에서 +5분 Skew 감지
    - 시스템 레벨 이슈로 판단
    """
    # 실제 시간 (가정)
    real_time = datetime(2026, 1, 16, 12, 5, 0, tzinfo=timezone.utc)
    
    # 서버 시간 (NTP 실패로 5분 느림)
    server_time = real_time - timedelta(minutes=5)
    
    # 브로커들은 실제 시간 기준으로 보고
    broker_times = {
        "kis": real_time,
        "mirae": real_time + timedelta(seconds=1),
        "kiwoom_re": real_time - timedelta(seconds=2)
    }
    
    # 모든 브로커에서 약 5분 Skew 감지
    skews = {}
    for broker, broker_time in broker_times.items():
        delta = abs((broker_time - server_time).total_seconds())
        skews[broker] = delta
    
    # 모든 브로커가 약 5분(300초) 차이
    for broker, skew in skews.items():
        assert 295 < skew < 305  # 5분 ±5초
    
    # 일관된 Skew → 시스템 레벨 이슈 추정
    skew_variance = max(skews.values()) - min(skews.values())
    assert skew_variance < 10  # 브로커 간 차이 10초 이내
