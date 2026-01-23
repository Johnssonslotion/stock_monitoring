"""
Redis Queue Manager

중앙 리퀘스트 큐 관리:
- api:request:queue (일반 태스크)
- api:priority:queue (우선순위 태스크)
"""
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Queue 키 정의
NORMAL_QUEUE = "api:request:queue"
PRIORITY_QUEUE = "api:priority:queue"


class QueueManager:
    """
    Redis 기반 태스크 큐 매니저

    우선순위 처리:
    - HIGH: api:priority:queue로 push
    - NORMAL: api:request:queue로 push
    - pop 시 priority queue 먼저 확인
    """

    def __init__(self, redis_client=None, redis_url: str = None):
        """
        Args:
            redis_client: 주입된 Redis 클라이언트 (테스트용)
            redis_url: Redis 연결 URL
        """
        self.redis = redis_client
        self.redis_url = redis_url

    async def connect(self):
        """Redis 연결 (redis_client가 없을 경우)"""
        if self.redis is None:
            import redis.asyncio as redis
            import os
            url = self.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis = await redis.from_url(url, decode_responses=True)
            logger.info(f"✅ QueueManager connected to Redis: {url}")

    async def push(self, task: dict) -> int:
        """
        태스크를 큐에 추가

        Args:
            task: 태스크 딕셔너리 (task_id, priority, provider 등)

        Returns:
            큐 길이
        """
        if self.redis is None:
            await self.connect()

        priority = task.get("priority", "NORMAL")
        queue_key = PRIORITY_QUEUE if priority == "HIGH" else NORMAL_QUEUE

        task_json = json.dumps(task, default=str)
        result = await self.redis.lpush(queue_key, task_json)

        logger.debug(f"📥 Task pushed to {queue_key}: {task.get('task_id')}")
        return result

    async def pop(self, queue_key: str = NORMAL_QUEUE) -> Optional[dict]:
        """
        특정 큐에서 태스크 pop

        Args:
            queue_key: 큐 키

        Returns:
            태스크 딕셔너리 또는 None
        """
        if self.redis is None:
            await self.connect()

        task_json = await self.redis.rpop(queue_key)

        if task_json is None:
            return None

        try:
            task = json.loads(task_json)
            logger.debug(f"📤 Task popped from {queue_key}: {task.get('task_id')}")
            return task
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse task: {e}")
            return None

    async def pop_with_priority(self) -> Optional[dict]:
        """
        우선순위 큐를 먼저 확인하고, 없으면 일반 큐에서 pop

        Returns:
            태스크 딕셔너리 또는 None
        """
        if self.redis is None:
            await self.connect()

        # 1. Priority queue 먼저 확인
        task = await self.pop(PRIORITY_QUEUE)
        if task is not None:
            return task

        # 2. Normal queue에서 pop
        return await self.pop(NORMAL_QUEUE)

    async def length(self, queue_key: str = None) -> int:
        """
        큐 길이 조회

        Args:
            queue_key: 특정 큐 (None이면 전체)

        Returns:
            큐 길이
        """
        if self.redis is None:
            await self.connect()

        if queue_key:
            return await self.redis.llen(queue_key)

        # 전체 길이
        priority_len = await self.redis.llen(PRIORITY_QUEUE)
        normal_len = await self.redis.llen(NORMAL_QUEUE)
        return priority_len + normal_len

    async def clear(self, queue_key: str = None):
        """
        큐 비우기 (테스트용)

        Args:
            queue_key: 특정 큐 (None이면 전체)
        """
        if self.redis is None:
            await self.connect()

        if queue_key:
            await self.redis.delete(queue_key)
        else:
            await self.redis.delete(PRIORITY_QUEUE)
            await self.redis.delete(NORMAL_QUEUE)

        logger.info("🗑️ Queue cleared")
