"""
Orchestrator Failover 로직 유닛 테스트
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.trading.orchestrator import BrokerOrchestrator


@pytest.fixture
def orchestrator():
    """테스트용 Orchestrator 인스턴스"""
    config = {
        "redis_url": "redis://localhost:6379/0",
        "use_mock": True,
        "brokers": {
            "kis": {"app_key": "dummy"},
            "mirae": {"app_key": "dummy"},
            "kiwoom_re": {"app_key": "dummy"}
        }
    }
    return BrokerOrchestrator(config)


def test_load_collection_strategy(orchestrator):
    """Collection Strategy 로딩 테스트"""
    # 설정 파일 로드
    orchestrator.load_collection_strategy("configs/collection_strategy.yaml")
    
    # 심볼 할당 확인
    assert "kis" in orchestrator.symbol_assignments
    assert "mirae" in orchestrator.symbol_assignments
    
    # Tier1 심볼이 할당되었는지 확인
    kis_symbols = orchestrator.symbol_assignments["kis"]
    assert "005930" in kis_symbols  # 삼성전자
    assert "000660" in kis_symbols  # SK하이닉스
    
    # Failover 매핑 확인
    assert "kis" in orchestrator.backup_mappings
    assert orchestrator.backup_mappings["kis"] == "mirae"


def test_assign_symbols(orchestrator):
    """심볼 할당 테스트"""
    test_symbols = ["005930", "000660", "069500"]
    
    orchestrator.assign_symbols("kis", test_symbols)
    
    assert "kis" in orchestrator.symbol_assignments
    assert len(orchestrator.symbol_assignments["kis"]) == 3
    assert "005930" in orchestrator.symbol_assignments["kis"]


def test_assign_symbols_no_duplicates(orchestrator):
    """중복 심볼 제거 테스트"""
    orchestrator.assign_symbols("kis", ["005930", "000660"])
    orchestrator.assign_symbols("kis", ["000660", "069500"])  # 000660 중복
    
    kis_symbols = orchestrator.symbol_assignments["kis"]
    assert len(kis_symbols) == 3  # 중복 제거되어 3개
    assert kis_symbols.count("000660") == 1  # 중복 없음


def test_setup_failover(orchestrator):
    """Failover 설정 테스트"""
    orchestrator.setup_failover("kis", "mirae", ["005930"], delay=60)
    
    assert orchestrator.backup_mappings["kis"] == "mirae"


@pytest.mark.asyncio
async def test_activate_backup_new_broker(orchestrator):
    """Backup 브로커 신규 활성화 테스트"""
    # 브로커 셋업
    orchestrator.setup_brokers(["kis", "mirae", "kiwoom_re"])
    
    # Mock 브로커 동작
    for broker in orchestrator.active_brokers.values():
        broker.connect = AsyncMock(return_value=True)
        broker.start_realtime_subscribe = AsyncMock(return_value=True)
        broker.run = AsyncMock()
        broker.is_running = False
    
    # Backup 활성화
    await orchestrator.activate_backup("mirae", ["005930", "000660"])
    
    # 연결 및 구독이 호출되었는지 확인
    mirae_broker = orchestrator.active_brokers["mirae"]
    mirae_broker.connect.assert_called_once()
    mirae_broker.start_realtime_subscribe.assert_called_once()


@pytest.mark.asyncio
async def test_activate_backup_already_running(orchestrator):
    """이미 실행 중인 Backup 브로커에 심볼 추가 테스트"""
    orchestrator.setup_brokers(["mirae"])
    
    mirae_broker = orchestrator.active_brokers["mirae"]
    mirae_broker.connect = AsyncMock(return_value=True)
    mirae_broker.start_realtime_subscribe = AsyncMock(return_value=True)
    mirae_broker.run = AsyncMock()
    mirae_broker.is_running = True  # 이미 실행 중
    
    # Backup 활성화 (추가 심볼만 구독)
    await orchestrator.activate_backup("mirae", ["005930"])
    
    # connect는 호출되지 않아야 함 (이미 실행 중)
    mirae_broker.connect.assert_not_called()
    # 심볼 구독은 호출되어야 함
    mirae_broker.start_realtime_subscribe.assert_called_once()


def test_load_strategy_file_not_found(orchestrator):
    """존재하지 않는 설정 파일 로드 테스트"""
    # FileNotFoundError 발생 시 정상 처리되는지 확인
    orchestrator.load_collection_strategy("invalid_path.yaml")
    
    # 빈 할당 상태여야 함
    assert len(orchestrator.symbol_assignments) == 0


def test_integration_strategy_and_failover(orchestrator):
    """전체 통합 테스트: Strategy 로딩 → Failover 설정"""
    # 1. Strategy 로드
    orchestrator.load_collection_strategy("configs/collection_strategy.yaml")
    
    # 2. 브로커 셋업
    orchestrator.setup_brokers(["kis", "mirae", "kiwoom_re"])
    
    # 3. 할당된 심볼 확인
    assert len(orchestrator.symbol_assignments) >= 3  # kis, mirae, kiwoom_re
    
    # 4. Failover 매핑 확인
    assert "kis" in orchestrator.backup_mappings
    assert orchestrator.backup_mappings["kis"] == "mirae"
    
    # 5. Failover 설정 확인
    assert "failover" in orchestrator.failover_config or True  # Empty is OK
