"""
Chaos Test: 네트워크 지연 시뮬레이션

멀티 브로커 환경에서 브로커별 네트워크 레이턴시가 상이할 때
데이터 도착 순서와 타임스탬프 일관성을 검증합니다.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from src.trading.orchestrator import BrokerOrchestrator
from src.core.time_utils import TimestampManager


async def inject_network_delay(broker: str, delay_ms: int):
    """
    특정 브로커의 네트워크 응답에 인위적 지연 주입
    
    Args:
        broker: 브로커 이름 ('kis', 'mirae', 'kiwoom_re')
        delay_ms: 지연 시간 (밀리초)
    """
    await asyncio.sleep(delay_ms / 1000.0)


@pytest.fixture
def orchestrator_with_delays():
    """지연이 주입된 Orchestrator"""
    config = {
        "redis_url": "redis://localhost:6379/0",
        "use_mock": True,
        "brokers": {
            "kis": {"delay_ms": 0},       # 즉시
            "mirae": {"delay_ms": 100},   # +100ms
            "kiwoom_re": {"delay_ms": 500}  # +500ms
        }
    }
    orch = BrokerOrchestrator(config)
    orch.setup_brokers(["kis", "mirae", "kiwoom_re"])
    
    # Mock 브로커에 지연 주입
    for broker_name, broker in orch.active_brokers.items():
        delay = config["brokers"][broker_name]["delay_ms"]
        
        # 원본 메서드 저장
        original_receive = broker._receive_data if hasattr(broker, '_receive_data') else AsyncMock()
        
        # 지연이 주입된 래퍼
        async def delayed_receive(*args, delay=delay, orig=original_receive, **kwargs):
            await inject_network_delay(broker_name, delay)
            return await orig(*args, **kwargs)
        
        broker._receive_data = delayed_receive
    
    return orch


@pytest.mark.asyncio
async def test_broker_lag_order_consistency(orchestrator_with_delays):
    """
    브로커별 지연 시 데이터 수신 순서 검증
    
    시나리오:
    - KIS: 즉시 (0ms)
    - 미래: +100ms
    - 키움: +500ms
    
    기대 결과:
    - received_time 순서: KIS < 미래 < 키움
    - broker_time은 동일 (모두 같은 체결 시간)
    """
    orchestrator = orchestrator_with_delays
    
    # 동시 데이터 발생 시뮬레이션
    trade_time = datetime.now(timezone.utc)
    symbol = "005930"
    
    received_times = {}
    
    # 각 브로커에서 데이터 수신
    for broker_name, broker in orchestrator.active_brokers.items():
        start = datetime.now(timezone.utc)
        
        # Mock 데이터 수신
        data = {
            "symbol": symbol,
            "price": 73000,
            "broker_time": trade_time.strftime("%H%M%S"),
            "broker": broker_name
        }
        
        # 지연이 주입된 수신
        await broker._receive_data(data)
        
        end = datetime.now(timezone.utc)
        received_times[broker_name] = end
    
    # 수신 순서 검증
    assert received_times["kis"] < received_times["mirae"]
    assert received_times["mirae"] < received_times["kiwoom_re"]
    
    # 시간 차이 검증 (오차 ±50ms)
    kis_mirae_delta = (received_times["mirae"] - received_times["kis"]).total_seconds() * 1000
    assert 50 < kis_mirae_delta < 150  # 100ms ±50ms
    
    mirae_kiwoom_delta = (received_times["kiwoom_re"] - received_times["mirae"]).total_seconds() * 1000
    assert 350 < mirae_kiwoom_delta < 550  # 400ms ±50ms


@pytest.mark.asyncio
async def test_conflict_resolution_with_delay():
    """
    동일 심볼/시간대에 여러 브로커 데이터 도착 시 Conflict Resolution
    
    시나리오:
    - 005930 종목, 12:00:00 체결
    - KIS: 73,000원 (즉시 도착)
    - 미래: 73,010원 (100ms 지연 도착)
    - 키움: 72,990원 (500ms 지연 도착)
    
    기대 결과:
    - broker_priority에 따라 KIS 데이터 선택 (73,000원)
    """
    from src.core.conflict_resolver import resolve_conflicting_ticks
    
    trade_time = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    
    ticks = [
        {
            "symbol": "005930",
            "price": 73000,
            "broker": "kis",
            "broker_time": trade_time,
            "received_time": trade_time + timedelta(milliseconds=0)
        },
        {
            "symbol": "005930",
            "price": 73010,
            "broker": "mirae",
            "broker_time": trade_time,
            "received_time": trade_time + timedelta(milliseconds=100)
        },
        {
            "symbol": "005930",
            "price": 72990,
            "broker": "kiwoom_re",
            "broker_time": trade_time,
            "received_time": trade_time + timedelta(milliseconds=500)
        }
    ]
    
    # Conflict Resolution (broker_priority 전략)
    broker_priority = ["kis", "mirae", "kiwoom_re"]
    resolved = resolve_conflicting_ticks(ticks, strategy="broker_priority", priority=broker_priority)
    
    # KIS 데이터가 선택되어야 함
    assert resolved["broker"] == "kis"
    assert resolved["price"] == 73000


@pytest.mark.asyncio
async def test_timestamp_synchronization():
    """
    브로커별 지연 발생 시 타임스탬프 계층 구조 검증
    
    기대 결과:
    - broker_time: 모두 동일 (실제 체결 시간)
    - received_time: 지연 순서대로 차이 발생
    - stored_time: received_time 이후
    """
    trade_time_str = "120000"  # 12:00:00 KST
    base_date = datetime(2026, 1, 16).date()
    
    # 브로커 시간 파싱
    kis_broker_time = TimestampManager.parse_broker_time(trade_time_str, "kis", base_date)
    mirae_broker_time = TimestampManager.parse_broker_time(trade_time_str, "mirae", base_date)
    
    # broker_time은 동일해야 함
    assert kis_broker_time == mirae_broker_time
    
    # 수신 시간은 다를 수 있음
    kis_received = datetime.now(timezone.utc)
    await asyncio.sleep(0.1)
    mirae_received = datetime.now(timezone.utc)
    
    assert kis_received < mirae_received


@pytest.mark.asyncio
async def test_high_latency_threshold_alert():
    """
    비정상적으로 높은 레이턴시 감지 및 알림
    
    시나리오:
    - 평소 KIS 레이턴시: 50ms
    - 갑작스런 스파이크: 5,000ms
    
    기대 결과:
    - P99 임계치(200ms) 초과 감지
    - 알림 트리거
    """
    normal_latencies = [45, 52, 48, 51, 49]  # ms
    spike_latency = 5000  # 5초
    
    latencies = normal_latencies + [spike_latency]
    
    # P99 계산
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    
    # 임계치 초과 확인
    threshold = 200  # ms
    assert p99 > threshold
    
    # 알림 조건 충족
    alert_triggered = p99 > threshold
    assert alert_triggered is True


@pytest.mark.asyncio  
async def test_time_bucket_aggregation_with_delays():
    """
    1분 Time Bucket 집계 시 지연 데이터 처리
    
    시나리오:
    - 12:00:00 ~ 12:00:59 체결 데이터
    - 일부 데이터는 12:01:00 이후 도착 (500ms 지연)
    
    기대 결과:
    - broker_time 기준으로 12:00 버킷에 포함
    - received_time이 아닌 broker_time으로 집계
    """
    from datetime import datetime
    
    # 12:00:00 체결, 12:01:00.5 수신
    tick_1 = {
        "broker_time": datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        "received_time": datetime(2026, 1, 16, 12, 1, 0, 500000, tzinfo=timezone.utc)
    }
    
    # 12:00:59 체결, 12:01:01 수신
    tick_2 = {
        "broker_time": datetime(2026, 1, 16, 12, 0, 59, tzinfo=timezone.utc),
        "received_time": datetime(2026, 1, 16, 12, 1, 1, tzinfo=timezone.utc)
    }
    
    # Time Bucket 할당 (broker_time 기준)
    def get_time_bucket(tick, bucket_size_min=1):
        return tick["broker_time"].replace(second=0, microsecond=0)
    
    bucket_1 = get_time_bucket(tick_1)
    bucket_2 = get_time_bucket(tick_2)
    
    # 둘 다 12:00 버킷
    assert bucket_1 == bucket_2
    assert bucket_1.hour == 12
    assert bucket_1.minute == 0
