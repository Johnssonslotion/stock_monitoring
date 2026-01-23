"""
API Hub Client - 외부에서 API Hub Queue를 통해 요청하는 클라이언트

BackfillManager, RecoveryOrchestrator 등에서 사용.
직접 API 호출 대신 Queue를 통해 Worker에게 요청.

Reference:
    - ISSUE-040: API Hub v2 Phase 2 - Real API Integration
"""
import asyncio
import logging
import os
import uuid
from typing import Dict, Any, Optional

from .queue import QueueManager

logger = logging.getLogger("APIHubClient")


class APIHubClient:
    """
    API Hub Queue 클라이언트

    외부 모듈에서 REST API 호출이 필요할 때 사용.
    직접 API 호출 대신 Queue에 태스크를 푸시하고 결과를 대기.

    Example:
        ```python
        client = APIHubClient()
        await client.connect()

        result = await client.execute(
            provider="KIS",
            tr_id="FHKST01010300",
            params={"symbol": "005930"}
        )
        ```
    """

    def __init__(self, redis_url: str = None):
        """
        Args:
            redis_url: Redis 연결 URL (기본: 환경변수 API_HUB_REDIS_URL 또는 REDIS_URL)
        """
        self.redis_url = redis_url or os.getenv(
            "API_HUB_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/15")
        )
        self.queue_manager: Optional[QueueManager] = None
        self._connected = False

    async def connect(self):
        """Redis 연결"""
        if not self._connected:
            self.queue_manager = QueueManager(redis_url=self.redis_url)
            await self.queue_manager.connect()
            self._connected = True
            logger.info(f"✅ APIHubClient connected to {self.redis_url}")

    async def disconnect(self):
        """연결 종료"""
        if self.queue_manager and self.queue_manager.redis:
            await self.queue_manager.redis.close()
            self._connected = False
            logger.info("🔴 APIHubClient disconnected")

    async def execute(
        self,
        provider: str,
        tr_id: str,
        params: Dict[str, Any],
        priority: str = "NORMAL",
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        API 요청 실행 (Queue 기반)

        Args:
            provider: 제공자 (KIS, KIWOOM)
            tr_id: 거래 ID (예: FHKST01010300)
            params: 요청 파라미터
            priority: 우선순위 (HIGH, NORMAL)
            timeout: 결과 대기 타임아웃 (초)

        Returns:
            결과 딕셔너리

        Raises:
            TimeoutError: 결과 대기 타임아웃
            ConnectionError: Redis 연결 안됨
        """
        if not self._connected:
            await self.connect()

        # 태스크 생성
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "provider": provider,
            "tr_id": tr_id,
            "params": params,
            "priority": priority
        }

        # Queue에 푸시하고 결과 대기
        result = await self.queue_manager.push_and_wait(task, timeout=timeout)

        if result is None:
            raise TimeoutError(
                f"API Hub timeout waiting for task {task_id} "
                f"(provider={provider}, tr_id={tr_id})"
            )

        return result

    async def execute_batch(
        self,
        tasks: list,
        timeout: float = 60.0,
        concurrency: int = 5
    ) -> list:
        """
        배치 요청 실행

        Args:
            tasks: 태스크 리스트 [{"provider": ..., "tr_id": ..., "params": ...}, ...]
            timeout: 개별 태스크 타임아웃
            concurrency: 동시 실행 수

        Returns:
            결과 리스트
        """
        if not self._connected:
            await self.connect()

        results = []
        semaphore = asyncio.Semaphore(concurrency)

        async def execute_with_semaphore(task_params):
            async with semaphore:
                try:
                    return await self.execute(
                        provider=task_params["provider"],
                        tr_id=task_params["tr_id"],
                        params=task_params.get("params", {}),
                        priority=task_params.get("priority", "NORMAL"),
                        timeout=timeout
                    )
                except Exception as e:
                    return {
                        "status": "ERROR",
                        "reason": str(e),
                        "params": task_params
                    }

        # 동시 실행
        coros = [execute_with_semaphore(t) for t in tasks]
        results = await asyncio.gather(*coros)

        return list(results)

    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()


# 편의를 위한 전역 인스턴스 (선택적)
_default_client: Optional[APIHubClient] = None


async def get_hub_client() -> APIHubClient:
    """전역 APIHubClient 인스턴스 반환"""
    global _default_client
    if _default_client is None:
        _default_client = APIHubClient()
        await _default_client.connect()
    return _default_client
