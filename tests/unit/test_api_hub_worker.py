"""
HUB-W-01: Worker 429 Handling (Pause & Re-queue)
HUB-W-02: Worker Rate Limiting Wait
HUB-W-03: Worker Priority Queue Processing
"""
import pytest
import json
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from src.api_gateway.hub.worker import RestApiWorker, MockClient
from src.api_gateway.hub.dispatcher import TaskDispatcher

class TestRestApiWorker:
    """RestApiWorker 기본 동작 테스트"""
    
    @pytest.mark.asyncio
    async def test_worker_initialization(self):
        """Worker 초기화"""
        worker = RestApiWorker(enable_mock=True)
        
        assert worker.enable_mock is True
        assert worker.is_running is False
        assert worker.circuit_breaker is not None
    
    @pytest.mark.asyncio
    async def test_mock_client_execute(self):
        """MockClient API 실행"""
        client = MockClient("KIS")
        
        result = await client.execute(
            tr_id="TEST_TR",
            params={"symbol": "005930"}
        )
        
        assert result["provider"] == "KIS"
        assert result["tr_id"] == "TEST_TR"
        assert result["result"] == "SUCCESS"
        assert result["data"]["symbol"] == "005930"
    
    @pytest.mark.asyncio
    async def test_worker_setup(self):
        """Worker setup 및 컴포넌트 초기화"""
        worker = RestApiWorker(redis_url="redis://localhost:6379/10")
        
        # Mock Redis 주입
        worker.queue_manager = MagicMock()
        worker.queue_manager.connect = AsyncMock()
        
        await worker.setup()
        
        assert worker.dispatcher is not None
        assert "KIS" in worker.dispatcher.clients
        assert "KIWOOM" in worker.dispatcher.clients
    
    @pytest.mark.asyncio
    async def test_worker_process_task_success(self):
        """태스크 정상 처리"""
        worker = RestApiWorker()
        await worker.setup()
        
        task = {
            "task_id": "test-001",
            "provider": "KIS",
            "tr_id": "TEST",
            "params": {"symbol": "005930"}
        }
        
        result = await worker.process_task(task)
        
        assert result["status"] == "SUCCESS"
        assert result["task_id"] == "test-001"
    
    @pytest.mark.asyncio
    async def test_worker_process_task_circuit_open(self):
        """Circuit Breaker OPEN 시 태스크 거부"""
        worker = RestApiWorker()
        await worker.setup()
        
        # Circuit Breaker 강제로 열기
        for _ in range(5):
            worker.circuit_breaker.record_failure()
        
        task = {
            "task_id": "test-002",
            "provider": "KIS",
            "tr_id": "TEST",
            "params": {}
        }
        
        result = await worker.process_task(task)
        
        assert result["status"] == "REJECTED"
        assert result["reason"] == "CIRCUIT_OPEN"


class TestWorkerIntegration:
    """Worker 통합 테스트 (blpop 포함)"""
    
    @pytest.mark.asyncio
    async def test_worker_run_and_stop(self):
        """Worker 실행 및 정상 종료"""
        worker = RestApiWorker(redis_url="redis://localhost:6379/10")
        
        # Mock setup method to prevent real Redis connection
        async def mock_setup():
            mock_redis = AsyncMock()
            
            # blpop이 항상 None을 반환하도록 설정
            # 이렇게 하면 worker는 계속 대기하다가 stop() 호출로 종료됨
            async def mock_blpop(*args, **kwargs):
                # 이벤트 루프에 제어권을 양보하여 auto_stop() 실행 가능하게 함
                await asyncio.sleep(0.01)
                return None
            
            mock_redis.blpop = mock_blpop
            mock_redis.aclose = AsyncMock()
            
            mock_queue_manager = MagicMock()
            mock_queue_manager.redis = mock_redis
            
            worker.queue_manager = mock_queue_manager
            worker.dispatcher = TaskDispatcher(
                circuit_breaker=worker.circuit_breaker,
                clients={}
            )
            worker.mode_str = "Mock" if worker.enable_mock else "Real API"
            worker._mock_redis = mock_redis  # Test용 저장
        
        worker.setup = mock_setup
        
        # 0.1초 후 자동 종료
        async def auto_stop():
            await asyncio.sleep(0.1)
            worker.stop()
        
        # 병렬 실행
        await asyncio.gather(
            worker.run(),
            auto_stop()
        )
        
        assert worker.is_running is False
        worker._mock_redis.aclose.assert_called_once()
