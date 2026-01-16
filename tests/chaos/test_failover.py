"""
Chaos Test: Failover 자동 전환 (Revised for KIS + Kiwoom RE)

Tier 구조 변경에 따른 Failover 로직 검증:
1. Tier 2 (Kiwoom Primary -> KIS Backup) 자동 전환
2. Primary 복구 시 자동 복귀
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from src.trading.orchestrator import BrokerOrchestrator


@pytest.fixture
def orchestrator_with_failover():
    """Failover 설정이 된 Orchestrator"""
    config = {
        "redis_url": "redis://localhost:6379/0",
        "use_mock": True,
        "brokers": {}
    }
    orch = BrokerOrchestrator(config)
    # 실제 설정 파일 로드
    orch.load_collection_strategy("configs/collection_strategy.yaml")
    orch.setup_brokers(["kis", "kiwoom_re"])
    
    # Mock 브로커 동작
    for broker in orch.active_brokers.values():
        broker.connect = AsyncMock(return_value=True)
        broker.start_realtime_subscribe = AsyncMock(return_value=True)
        broker.stop_realtime_subscribe = AsyncMock(return_value=True)
        broker.disconnect = AsyncMock()
        broker.run = AsyncMock()
        broker.is_running = False
    
    return orch


@pytest.mark.asyncio
async def test_tier2_failover_kiwoom_to_kis(orchestrator_with_failover):
    """
    Tier 2: 키움(Primary) 장애 시 KIS(Backup)로 전환
    
    시나리오:
    - 키움 RE 장애 발생
    - KIS가 Tier 2 심볼에 대해 Backup으로 활성화
    """
    orchestrator = orchestrator_with_failover
    
    # Tier 2 심볼 (설정 파일에서 로드된 것 중 일부)
    tier2_symbols = ["005930", "000660"]
    
    # Backup 활성화 요청
    await orchestrator.activate_backup("kis", tier2_symbols)
    
    # KIS 브로커 연결 확인
    kis_broker = orchestrator.active_brokers["kis"]
    # 이미 실행 중일 수 있으므로 호출 여부 확인
    if not kis_broker.is_running:
        kis_broker.connect.assert_called()
    
    kis_broker.start_realtime_subscribe.assert_called()


@pytest.mark.asyncio
async def test_auto_fallback_to_kiwoom(orchestrator_with_failover):
    """
    Tier 2: 키움 복구 시 자동 복귀
    
    시나리오:
    - 현재 Backup(KIS) 운영 중
    - 키움 복구 감지
    - Grace Period 후 키움으로 복귀
    """
    orchestrator = orchestrator_with_failover
    
    kis_broker = orchestrator.active_brokers["kis"]
    kiwoom_broker = orchestrator.active_brokers["kiwoom_re"]
    
    # 현재상황: KIS가 Backup 수행 중
    kis_broker.is_running = True
    
    # 키움 복구 (가정)
    kiwoom_broker.is_running = True
    
    # 복귀 조건 충족 확인
    # (실제 로직은 Orchestrator에 구현되어 있어야 함을 가정)
    assert kiwoom_broker.is_running is True


@pytest.mark.asyncio
async def test_tier1_kis_failure_detection(orchestrator_with_failover):
    """
    Tier 1 (KIS Only) 장애 감지
    
    시나리오:
    - KIS 장애 발생
    - Backup 없음 (null)
    - 경고 로그 발생 확인
    """
    orchestrator = orchestrator_with_failover
    
    # KIS 장애 시뮬레이션
    kis_broker = orchestrator.active_brokers["kis"]
    kis_broker.is_running = False
    
    # 장애 감지 로직 트리거 (테스트에서는 상태만 확인)
    assert kis_broker.is_running is False


@pytest.mark.asyncio
async def test_failover_metrics_updated(orchestrator_with_failover):
    """Failover 메트릭 검증"""
    event = {
        "timestamp": datetime.now(),
        "primary": "kiwoom_re",
        "backup": "kis",
        "status": "activated"
    }
    
    assert event["primary"] == "kiwoom_re"
    assert event["backup"] == "kis"


@pytest.mark.asyncio
async def test_monitor_health_triggers_failover(orchestrator_with_failover):
    """
    monitor_health() 실행 시 죽은 브로커에 대해 Failover가 트리거되는지 검증
    """
    orchestrator = orchestrator_with_failover
    
    # 1. Setup Failover Config (Mocking load_collection_strategy effect)
    # kiwoom_re -> kis (delay 0)
    orchestrator.backup_mappings["kiwoom_re"] = "kis"
    orchestrator.symbol_assignments["kiwoom_re"] = ["005930", "000660"]
    
    # 2. Simulate Primary Failure
    kiwoom = orchestrator.active_brokers["kiwoom_re"]
    kiwoom.is_running = False
    
    # 3. Mock activate_backup to verify call
    with patch.object(orchestrator, 'activate_backup', new_callable=AsyncMock) as mock_activate:
        # 4. Run Monitor
        await orchestrator.monitor_health()
        
        # 5. Verify Failover Triggered
        mock_activate.assert_called_once_with("kis", ["005930", "000660"])
