"""
HUB-CB-01: Circuit Breaker - 연속 실패 시 backpressure 동작
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone


class TestCircuitBreaker:
    """HUB-CB-01: Circuit Breaker 테스트"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """연속 실패 시 회로 차단"""
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        # 3번 연속 실패
        for _ in range(3):
            cb.record_failure()

        assert cb.is_open() is True
        assert cb.state == "OPEN"

    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_when_closed(self):
        """회로 닫힘 상태에서는 요청 허용"""
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        assert cb.is_open() is False
        assert cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self):
        """회로 열림 상태에서는 요청 차단"""
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        # 회로 열기
        for _ in range(3):
            cb.record_failure()

        assert cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """성공 시 실패 카운트 리셋"""
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        # 2번 실패 후 성공
        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        assert cb.failure_count == 0
        assert cb.is_open() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state(self):
        """반열림 상태에서 테스트 요청 허용"""
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # 회로 열기
        for _ in range(3):
            cb.record_failure()

        assert cb.is_open() is True

        # recovery_timeout 후 half-open
        import asyncio
        await asyncio.sleep(0.15)

        assert cb.state == "HALF_OPEN"
        assert cb.can_execute() is True  # 테스트 요청 허용

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_success_in_half_open(self):
        """반열림 상태에서 성공하면 회로 닫힘"""
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # 회로 열기
        for _ in range(3):
            cb.record_failure()

        import asyncio
        await asyncio.sleep(0.15)

        # half-open 상태에서 성공
        cb.record_success()

        assert cb.state == "CLOSED"
        assert cb.failure_count == 0


class TestDispatcherWithCircuitBreaker:
    """Dispatcher + Circuit Breaker 통합"""

    @pytest.mark.asyncio
    async def test_dispatcher_respects_circuit_breaker(self):
        """Dispatcher가 Circuit Breaker 상태를 존중"""
        from src.api_gateway.hub.dispatcher import TaskDispatcher
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30)
        dispatcher = TaskDispatcher(circuit_breaker=cb)

        # 회로 열기
        cb.record_failure()
        cb.record_failure()

        task = {"task_id": "test-001", "provider": "KIS"}
        result = await dispatcher.dispatch(task)

        assert result["status"] == "REJECTED"
        assert result["reason"] == "CIRCUIT_OPEN"

    @pytest.mark.asyncio
    async def test_dispatcher_processes_when_circuit_closed(self):
        """회로 닫힘 시 정상 처리"""
        from src.api_gateway.hub.dispatcher import TaskDispatcher
        from src.api_gateway.hub.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        # Mock client
        mock_client = AsyncMock()
        mock_client.execute = AsyncMock(return_value={"data": "success"})

        dispatcher = TaskDispatcher(
            circuit_breaker=cb,
            clients={"KIS": mock_client}
        )

        task = {"task_id": "test-002", "provider": "KIS", "tr_id": "TEST"}
        result = await dispatcher.dispatch(task)

        assert result["status"] == "SUCCESS"
        mock_client.execute.assert_called_once()


class TestDispatcherWithRateLimiter:
    """Dispatcher + Rate Limiter 연동 테스트"""

    @pytest.mark.asyncio
    async def test_dispatcher_respects_rate_limiter_allow(self):
        """Rate Limiter 허용 시 정상 실행"""
        from src.api_gateway.hub.dispatcher import TaskDispatcher
        
        mock_limiter = AsyncMock()
        mock_limiter.wait_acquire = AsyncMock(return_value=True)
        
        mock_client = AsyncMock()
        mock_client.execute = AsyncMock(return_value={"data": "ok"})
        
        dispatcher = TaskDispatcher(clients={"KIS": mock_client}, rate_limiter=mock_limiter)
        
        task = {"task_id": "rl-001", "provider": "KIS", "tr_id": "TEST"}
        result = await dispatcher.dispatch(task)
        
        assert result["status"] == "SUCCESS"
        mock_limiter.wait_acquire.assert_called_with("KIS", timeout=5.0)

    @pytest.mark.asyncio
    async def test_dispatcher_respects_rate_limiter_timeout(self):
        """Rate Limiter 타임아웃 시 RATE_LIMITED 반환"""
        from src.api_gateway.hub.dispatcher import TaskDispatcher
        
        mock_limiter = AsyncMock()
        mock_limiter.wait_acquire = AsyncMock(return_value=False)
        
        mock_client = AsyncMock()
        
        dispatcher = TaskDispatcher(clients={"KIS": mock_client}, rate_limiter=mock_limiter)
        
        task = {"task_id": "rl-002", "provider": "KIS", "tr_id": "TEST"}
        result = await dispatcher.dispatch(task)
        
        assert result["status"] == "RATE_LIMITED"
        assert result["reason"] == "RATE_LIMIT_TIMEOUT"
        mock_client.execute.assert_not_called()
