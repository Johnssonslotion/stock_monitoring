"""
Task Dispatcher

태스크를 적절한 클라이언트로 라우팅하고,
Circuit Breaker와 Rate Limiter를 적용합니다.
"""
import logging
from typing import Dict, Any, Optional
from .circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """
    태스크 디스패처

    역할:
    - 태스크를 provider(KIS/KIWOOM)에 따라 라우팅
    - Circuit Breaker 상태 확인 후 실행 결정
    - 실행 결과에 따라 Circuit Breaker 상태 업데이트
    """

    def __init__(
        self,
        circuit_breaker: CircuitBreaker = None,
        clients: Dict[str, Any] = None,
        rate_limiter=None
    ):
        """
        Args:
            circuit_breaker: Circuit Breaker 인스턴스
            clients: provider별 클라이언트 딕셔너리 {"KIS": client, ...}
            rate_limiter: Rate Limiter 인스턴스 (optional)
        """
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.clients = clients or {}
        self.rate_limiter = rate_limiter

    def register_client(self, provider: str, client):
        """클라이언트 등록"""
        self.clients[provider] = client
        logger.info(f"📝 Registered client for provider: {provider}")

    async def dispatch(self, task: dict) -> dict:
        """
        태스크 디스패치

        Args:
            task: 태스크 딕셔너리 (task_id, provider, tr_id, params 등)

        Returns:
            실행 결과 딕셔너리 (status, data/error 등)
        """
        task_id = task.get("task_id", "unknown")
        provider = task.get("provider")
        tr_id = task.get("tr_id")
        params = task.get("params", {})

        # 1. Circuit Breaker 확인
        if not self.circuit_breaker.can_execute():
            logger.warning(
                f"⛔ Task {task_id} rejected: Circuit Breaker OPEN"
            )
            return {
                "task_id": task_id,
                "status": "REJECTED",
                "reason": "CIRCUIT_OPEN",
                "circuit_state": self.circuit_breaker.get_status()
            }

        # 2. 클라이언트 확인
        client = self.clients.get(provider)
        if client is None:
            logger.error(f"❌ No client registered for provider: {provider}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "reason": f"NO_CLIENT_{provider}"
            }

        # 3. Rate Limiter 확인 (optional)
        if self.rate_limiter:
            acquired = await self.rate_limiter.wait_acquire(provider, timeout=5.0)
            if not acquired:
                logger.warning(f"⏳ Task {task_id} rate limited")
                return {
                    "task_id": task_id,
                    "status": "RATE_LIMITED",
                    "reason": "RATE_LIMIT_TIMEOUT"
                }

        # 4. 실행
        try:
            result = await client.execute(tr_id=tr_id, params=params)

            # 성공 기록
            self.circuit_breaker.record_success()

            logger.info(f"✅ Task {task_id} completed successfully")
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "data": result
            }

        except Exception as e:
            # 실패 기록
            self.circuit_breaker.record_failure()

            logger.error(f"❌ Task {task_id} failed: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "reason": str(e),
                "circuit_state": self.circuit_breaker.get_status()
            }

    async def dispatch_batch(self, tasks: list) -> list:
        """
        배치 디스패치

        Args:
            tasks: 태스크 리스트

        Returns:
            결과 리스트
        """
        results = []
        for task in tasks:
            result = await self.dispatch(task)
            results.append(result)

            # Circuit Breaker가 열리면 나머지 태스크 거부
            if not self.circuit_breaker.can_execute():
                for remaining in tasks[len(results):]:
                    results.append({
                        "task_id": remaining.get("task_id", "unknown"),
                        "status": "REJECTED",
                        "reason": "CIRCUIT_OPEN"
                    })
                break

        return results

    def get_status(self) -> dict:
        """디스패처 상태 정보"""
        return {
            "circuit_breaker": self.circuit_breaker.get_status(),
            "registered_clients": list(self.clients.keys()),
            "rate_limiter_enabled": self.rate_limiter is not None
        }
