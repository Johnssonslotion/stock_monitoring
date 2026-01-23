"""
HUB-INT-01: Full Request-Response Flow (Mock Mode)

이 테스트는 RestApiWorker의 전체 통합 플로우를 검증합니다:
Queue -> Worker -> Dispatcher -> MockClient -> Response

⚠️ 이 테스트는 실제 Redis가 필요하므로 CI에서 제외됩니다.
실행 방법: pytest -m manual tests/integration/test_api_hub_v2_integration.py
"""
import pytest
import json
import asyncio
import uuid
from redis.asyncio import Redis
from src.api_gateway.hub.worker import RestApiWorker
from src.api_gateway.hub.queue import QueueManager, PRIORITY_QUEUE, NORMAL_QUEUE


@pytest.mark.manual
@pytest.mark.asyncio
async def test_full_api_hub_flow_integration():
    """
    RestApiWorker 전체 플로우 통합 테스트
    
    시나리오:
    1. Redis 큐에 태스크 푸시 (KIS Mock API 호출)
    2. RestApiWorker가 태스크를 pop하고 처리
    3. MockClient가 샘플 데이터 반환
    4. 결과 검증
    """
    redis_url = "redis://localhost:6379/15"  # Hub 전용 DB
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    try:
        # Clean state
        await redis.flushdb()
        
        # 1. Setup Components
        queue_manager = QueueManager(redis_url=redis_url)
        await queue_manager.connect()
        
        worker = RestApiWorker(redis_url=redis_url, enable_mock=True)
        
        # 2. Push Task to Normal Queue
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "provider": "KIS",
            "tr_id": "FHKST01010100",
            "params": {"symbol": "005930"}
        }
        
        await queue_manager.push(task)
        
        # Verify task in queue
        queue_len = await redis.llen(NORMAL_QUEUE)
        assert queue_len == 1, "Task should be in normal queue"
        
        # 3. Process Task (Single iteration)
        await worker.setup()
        
        # Pop and process one task
        result = await worker.queue_manager.redis.blpop([PRIORITY_QUEUE, NORMAL_QUEUE], timeout=1)
        assert result is not None, "Task should be available"
        
        queue_key, task_json = result
        task_from_queue = json.loads(task_json)
        
        # Process task
        response = await worker.process_task(task_from_queue)
        
        # 4. Verify Response
        assert response is not None
        assert response["status"] == "SUCCESS"
        assert response["data"]["provider"] == "KIS"
        assert response["data"]["tr_id"] == "FHKST01010100"
        assert response["data"]["params"]["symbol"] == "005930"
        assert response["data"]["result"] == "SUCCESS"
        
        # Cleanup
        await worker.cleanup()
        await queue_manager.redis.aclose()
        
    finally:
        await redis.aclose()


@pytest.mark.manual
@pytest.mark.asyncio
async def test_priority_queue_precedence():
    """
    우선순위 큐가 일반 큐보다 먼저 처리되는지 검증
    
    시나리오:
    1. Normal 큐에 태스크 2개 푸시
    2. Priority 큐에 태스크 1개 푸시
    3. Worker가 Priority 태스크를 먼저 처리하는지 확인
    """
    redis_url = "redis://localhost:6379/15"
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    try:
        await redis.flushdb()
        
        queue_manager = QueueManager(redis_url=redis_url)
        await queue_manager.connect()
        
        worker = RestApiWorker(redis_url=redis_url, enable_mock=True)
        await worker.setup()
        
        # Push 2 normal tasks
        task1 = {"task_id": "normal-1", "provider": "KIS", "tr_id": "TEST", "priority": "NORMAL"}
        task2 = {"task_id": "normal-2", "provider": "KIWOOM", "tr_id": "TEST", "priority": "NORMAL"}
        await queue_manager.push(task1)
        await queue_manager.push(task2)
        
        # Push 1 priority task
        task_priority = {"task_id": "priority-1", "provider": "KIS", "tr_id": "URGENT", "priority": "HIGH"}
        await queue_manager.push(task_priority)
        
        # Verify queue lengths
        assert await redis.llen(NORMAL_QUEUE) == 2
        assert await redis.llen(PRIORITY_QUEUE) == 1
        
        # Pop first task (should be priority)
        result = await worker.queue_manager.redis.blpop([PRIORITY_QUEUE, NORMAL_QUEUE], timeout=1)
        queue_key, task_json = result
        first_task = json.loads(task_json)
        
        assert first_task["task_id"] == "priority-1", "Priority task should be processed first"
        assert queue_key == PRIORITY_QUEUE
        
        # Cleanup
        await worker.cleanup()
        await queue_manager.redis.aclose()
        
    finally:
        await redis.aclose()


@pytest.mark.manual
@pytest.mark.asyncio
async def test_worker_graceful_shutdown():
    """
    Worker의 Graceful Shutdown 검증
    
    시나리오:
    1. Worker 시작
    2. 태스크 처리 중 stop() 호출
    3. is_running=False로 루프 종료 확인
    """
    redis_url = "redis://localhost:6379/15"
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    try:
        await redis.flushdb()
        
        worker = RestApiWorker(redis_url=redis_url, enable_mock=True)
        
        # Start worker in background
        worker_task = asyncio.create_task(worker.run())
        
        # Wait for setup
        await asyncio.sleep(0.5)
        
        # Verify worker is running
        assert worker.is_running is True
        
        # Stop worker
        worker.stop()
        
        # Wait for graceful shutdown
        await asyncio.wait_for(worker_task, timeout=3.0)
        
        # Verify worker stopped
        assert worker.is_running is False
        
    except asyncio.TimeoutError:
        pytest.fail("Worker did not stop gracefully within timeout")
    
    finally:
        await redis.aclose()


@pytest.mark.manual
@pytest.mark.asyncio
async def test_mock_client_both_providers():
    """
    MockClient가 KIS와 KIWOOM 모두 처리하는지 검증
    
    시나리오:
    1. KIS 태스크 푸시 및 처리
    2. KIWOOM 태스크 푸시 및 처리
    3. 각 provider별 응답 검증
    """
    redis_url = "redis://localhost:6379/15"
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    try:
        await redis.flushdb()
        
        queue_manager = QueueManager(redis_url=redis_url)
        await queue_manager.connect()
        
        worker = RestApiWorker(redis_url=redis_url, enable_mock=True)
        await worker.setup()
        
        # Test KIS
        kis_task = {
            "task_id": str(uuid.uuid4()),
            "provider": "KIS",
            "tr_id": "FHKST01010100",
            "params": {"symbol": "005930"}
        }
        await queue_manager.push(kis_task)
        
        result = await worker.queue_manager.redis.blpop([PRIORITY_QUEUE, NORMAL_QUEUE], timeout=1)
        _, task_json = result
        kis_response = await worker.process_task(json.loads(task_json))
        
        assert kis_response["status"] == "SUCCESS"
        assert kis_response["data"]["provider"] == "KIS"
        
        # Test KIWOOM
        kiwoom_task = {
            "task_id": str(uuid.uuid4()),
            "provider": "KIWOOM",
            "tr_id": "opt10081",
            "params": {"symbol": "005930"}
        }
        await queue_manager.push(kiwoom_task)
        
        result = await worker.queue_manager.redis.blpop([PRIORITY_QUEUE, NORMAL_QUEUE], timeout=1)
        _, task_json = result
        kiwoom_response = await worker.process_task(json.loads(task_json))
        
        assert kiwoom_response["status"] == "SUCCESS"
        assert kiwoom_response["data"]["provider"] == "KIWOOM"
        
        # Cleanup
        await worker.cleanup()
        await queue_manager.redis.aclose()
        
    finally:
        await redis.aclose()


if __name__ == "__main__":
    # Manual execution
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "-m", "manual"]))
