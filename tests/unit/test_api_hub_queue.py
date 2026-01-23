"""
HUB-Q-01: Redis 큐 push/pop, 우선순위 처리
HUB-Q-02: HIGH 우선순위 태스크 선처리
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestQueueManager:
    """HUB-Q-01: Redis 큐 push/pop 테스트"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis 클라이언트"""
        redis_mock = AsyncMock()
        redis_mock.lpush = AsyncMock(return_value=1)
        redis_mock.rpop = AsyncMock(return_value=None)
        redis_mock.llen = AsyncMock(return_value=0)
        return redis_mock

    @pytest.mark.asyncio
    async def test_push_task_to_queue(self, mock_redis):
        """태스크를 큐에 push"""
        from src.api_gateway.hub.queue import QueueManager

        manager = QueueManager(redis_client=mock_redis)

        task = {
            "task_id": "test-uuid-001",
            "priority": "NORMAL",
            "provider": "KIS",
            "tr_id": "FHKST03010200",
            "params": {"symbol": "005930"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await manager.push(task)

        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert "api:request:queue" in call_args[0]

    @pytest.mark.asyncio
    async def test_pop_task_from_queue(self, mock_redis):
        """태스크를 큐에서 pop"""
        from src.api_gateway.hub.queue import QueueManager

        expected_task = {
            "task_id": "test-uuid-002",
            "provider": "KIS"
        }
        mock_redis.rpop = AsyncMock(return_value=json.dumps(expected_task))

        manager = QueueManager(redis_client=mock_redis)
        task = await manager.pop()

        assert task is not None
        assert task["task_id"] == "test-uuid-002"

    @pytest.mark.asyncio
    async def test_pop_returns_none_when_empty(self, mock_redis):
        """큐가 비어있으면 None 반환"""
        from src.api_gateway.hub.queue import QueueManager

        mock_redis.rpop = AsyncMock(return_value=None)

        manager = QueueManager(redis_client=mock_redis)
        task = await manager.pop()

        assert task is None


class TestPriorityDispatch:
    """HUB-Q-02: HIGH 우선순위 선처리"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis with priority queue"""
        redis_mock = AsyncMock()
        return redis_mock

    @pytest.mark.asyncio
    async def test_priority_queue_checked_first(self, mock_redis):
        """우선순위 큐가 먼저 확인됨"""
        from src.api_gateway.hub.queue import QueueManager

        priority_task = {"task_id": "priority-001", "priority": "HIGH"}
        normal_task = {"task_id": "normal-001", "priority": "NORMAL"}

        # Priority 큐에 태스크 있음
        mock_redis.rpop = AsyncMock(side_effect=[
            json.dumps(priority_task),  # 첫 번째 호출: priority queue
            json.dumps(normal_task)     # 두 번째 호출: normal queue
        ])

        manager = QueueManager(redis_client=mock_redis)
        task = await manager.pop_with_priority()

        assert task["task_id"] == "priority-001"
        assert task["priority"] == "HIGH"

    @pytest.mark.asyncio
    async def test_fallback_to_normal_queue(self, mock_redis):
        """우선순위 큐가 비면 일반 큐에서 pop"""
        from src.api_gateway.hub.queue import QueueManager

        normal_task = {"task_id": "normal-001", "priority": "NORMAL"}

        # Priority 큐 비어있음, Normal 큐에 태스크 있음
        mock_redis.rpop = AsyncMock(side_effect=[
            None,                       # priority queue 비어있음
            json.dumps(normal_task)     # normal queue
        ])

        manager = QueueManager(redis_client=mock_redis)
        task = await manager.pop_with_priority()

        assert task["task_id"] == "normal-001"

    @pytest.mark.asyncio
    async def test_push_high_priority(self, mock_redis):
        """HIGH 우선순위 태스크는 priority 큐로"""
        from src.api_gateway.hub.queue import QueueManager

        mock_redis.lpush = AsyncMock(return_value=1)

        manager = QueueManager(redis_client=mock_redis)

        task = {
            "task_id": "urgent-001",
            "priority": "HIGH",
            "provider": "KIS"
        }

        await manager.push(task)

        call_args = mock_redis.lpush.call_args
        assert "api:priority:queue" in call_args[0]
