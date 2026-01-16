"""
TimestampManager 유닛 테스트
"""
import pytest
from datetime import datetime, timezone, timedelta
import pytz
from src.core.time_utils import TimestampManager, TimestampValidationError

KST = pytz.timezone('Asia/Seoul')


def test_now_utc():
    """UTC 시간 생성 테스트"""
    now = TimestampManager.now_utc()
    
    assert now.tzinfo == timezone.utc
    assert isinstance(now, datetime)
    
    # 현재 시간과의 차이가 1초 이내여야 함
    delta = abs((datetime.now(timezone.utc) - now).total_seconds())
    assert delta < 1.0


def test_now_kst():
    """KST 시간 생성 테스트"""
    now = TimestampManager.now_kst()
    
    assert now.tzinfo.zone == 'Asia/Seoul'
    assert isinstance(now, datetime)


def test_parse_broker_time_kis():
    """KIS 시간 포맷 파싱 테스트"""
    # "153045" = 15:30:45 KST
    base_date = datetime(2026, 1, 16).date()
    result = TimestampManager.parse_broker_time("153045", "kis", base_date)
    
    # UTC로 변환되어야 함 (KST - 9시간 = UTC)
    expected_utc = datetime(2026, 1, 16, 6, 30, 45, tzinfo=timezone.utc)
    assert result == expected_utc


def test_parse_broker_time_mirae():
    """미래에셋 시간 포맷 파싱 테스트"""
    base_date = datetime(2026, 1, 16).date()
    result = TimestampManager.parse_broker_time("093000", "mirae", base_date)
    
    # 09:30:00 KST = 00:30:00 UTC
    expected_utc = datetime(2026, 1, 16, 0, 30, 0, tzinfo=timezone.utc)
    assert result == expected_utc


def test_parse_broker_time_invalid_format():
    """잘못된 시간 포맷 테스트"""
    with pytest.raises(TimestampValidationError):
        TimestampManager.parse_broker_time("12345", "kis")  # 5자리 (잘못됨)


def test_parse_broker_time_unknown_broker():
    """알 수 없는 브로커 테스트"""
    with pytest.raises(TimestampValidationError):
        TimestampManager.parse_broker_time("120000", "unknown_broker")


def test_validate_skew_within_tolerance():
    """허용 오차 내 시간 차이 테스트"""
    reference = TimestampManager.now_utc()
    broker_time = reference + timedelta(seconds=3)  # +3초
    
    assert TimestampManager.validate_skew(broker_time, tolerance_sec=5, reference_time=reference) is True


def test_validate_skew_exceeds_tolerance():
    """허용 오차 초과 테스트"""
    reference = TimestampManager.now_utc()
    broker_time = reference + timedelta(seconds=10)  # +10초
    
    assert TimestampManager.validate_skew(broker_time, tolerance_sec=5, reference_time=reference) is False


def test_to_kst():
    """UTC → KST 변환 테스트"""
    utc_time = datetime(2026, 1, 16, 6, 0, 0, tzinfo=timezone.utc)
    kst_time = TimestampManager.to_kst(utc_time)
    
    # 6:00 UTC = 15:00 KST
    assert kst_time.hour == 15
    assert kst_time.tzinfo.zone == 'Asia/Seoul'


def test_to_utc():
    """KST → UTC 변환 테스트"""
    kst_time = KST.localize(datetime(2026, 1, 16, 15, 0, 0))
    utc_time = TimestampManager.to_utc(kst_time)
    
    # 15:00 KST = 6:00 UTC
    assert utc_time.hour == 6
    assert utc_time.tzinfo == timezone.utc


def test_format_and_parse_iso():
    """ISO 8601 포맷 변환 왕복 테스트"""
    original = TimestampManager.now_utc()
    
    # datetime → str → datetime
    iso_str = TimestampManager.format_iso(original)
    parsed = TimestampManager.parse_iso(iso_str)
    
    # 마이크로초 단위까지 동일해야 함
    assert original == parsed


def test_naive_datetime_handling():
    """Naive datetime 처리 테스트"""
    naive_utc = datetime(2026, 1, 16, 12, 0, 0)  # tzinfo 없음
    
    # to_kst는 UTC로 가정
    kst_result = TimestampManager.to_kst(naive_utc)
    assert kst_result.hour == 21  # 12:00 UTC = 21:00 KST
    
    # to_utc는 KST로 가정
    naive_kst = datetime(2026, 1, 16, 15, 0, 0)
    utc_result = TimestampManager.to_utc(naive_kst)
    assert utc_result.hour == 6  # 15:00 KST = 6:00 UTC
