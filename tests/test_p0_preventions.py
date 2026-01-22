import pytest
import importlib
import pkgutil
import src
import json
from src.data_ingestion.price.kr.kiwoom_ws import KiwoomWSCollector
from src.data_ingestion.price.common.websocket_dual import DualWebSocketManager

def test_smoke_imports():
    """전체 src 모듈의 ImportError 및 SyntaxError 여부 검증"""
    package = src
    prefix = package.__name__ + "."
    for loader, modname, ispkg in pkgutil.walk_packages(package.__path__, prefix):
        try:
            importlib.import_module(modname)
        except Exception as e:
            pytest.fail(f"Failed to import {modname}: {e}")

def test_kiwoom_login_structure():
    """Kiwoom LOGIN 메시지가 805002 오류를 유발하지 않는 FLAT 구조인지 검증"""
    collector = KiwoomWSCollector(
        app_key="test",
        app_secret="test",
        symbol_configs={"005930": ["0D"]},
        mock_mode=True
    )
    collector.token = "test_token"
    
    # Mocking ws.send
    sent_msgs = []
    class MockWS:
        async def send(self, msg):
            sent_msgs.append(json.loads(msg))
        async def recv(self):
            return json.dumps({"trnm": "LOGIN", "return_code": 0})
            
    collector.ws = MockWS()
    
    import asyncio
    asyncio.run(collector._send_login())
    
    login_msg = sent_msgs[0]
    # FLAT 구조 검증: header/body 중첩이 없어야 함
    assert "token" in login_msg
    assert "trnm" in login_msg
    assert "header" not in login_msg
    assert login_msg["trnm"] == "LOGIN"

def test_kis_subscription_limit_logic():
    """KIS 수집기가 시장 전환 시 이전 구독을 해지하는지 로직 검증 (MAX SUBSCRIBE OVER 방지)"""
    manager = DualWebSocketManager()
    
    # Mocking unsubscribe_market
    unsubscribed = []
    async def mock_unsubscribe(market):
        unsubscribed.append(market)
    
    manager.unsubscribe_market = mock_unsubscribe
    manager.active_markets = {"US"}
    
    import asyncio
    # KR로 전환 시도
    asyncio.run(manager.subscribe_market("KR"))
    
    # US가 해지되었는지 확인
    assert "US" in unsubscribed
