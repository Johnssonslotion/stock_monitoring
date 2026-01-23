"""
Circuit Breaker 패턴 구현

장애 전파 방지:
- CLOSED: 정상 상태, 요청 허용
- OPEN: 장애 상태, 요청 차단
- HALF_OPEN: 복구 테스트 중, 제한적 요청 허용
"""
import time
import logging
from typing import Literal

logger = logging.getLogger(__name__)

State = Literal["CLOSED", "OPEN", "HALF_OPEN"]


class CircuitBreaker:
    """
    Circuit Breaker 패턴

    연속 실패 시 회로를 열어 장애 전파를 방지하고,
    일정 시간 후 반열림 상태에서 복구를 시도합니다.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        name: str = "default"
    ):
        """
        Args:
            failure_threshold: 회로 열림 임계값 (연속 실패 횟수)
            recovery_timeout: 반열림 전환 대기 시간 (초)
            name: Circuit Breaker 이름 (로깅용)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self._state: State = "CLOSED"
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._success_count_in_half_open = 0

    @property
    def state(self) -> State:
        """현재 상태 (시간 기반 자동 전환 포함)"""
        if self._state == "OPEN":
            # recovery_timeout 경과 시 HALF_OPEN으로 전환
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                logger.info(
                    f"🔄 CircuitBreaker[{self.name}]: OPEN -> HALF_OPEN "
                    f"(after {elapsed:.1f}s)"
                )
        return self._state

    @property
    def failure_count(self) -> int:
        """현재 실패 횟수"""
        return self._failure_count

    def is_open(self) -> bool:
        """회로가 열려있는지 확인"""
        return self.state == "OPEN"

    def can_execute(self) -> bool:
        """요청 실행 가능 여부"""
        current_state = self.state

        if current_state == "CLOSED":
            return True

        if current_state == "HALF_OPEN":
            # 반열림 상태에서는 테스트 요청 허용
            return True

        # OPEN 상태
        return False

    def record_failure(self):
        """실패 기록"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            if self._state != "OPEN":
                self._state = "OPEN"
                logger.warning(
                    f"🔴 CircuitBreaker[{self.name}]: OPEN "
                    f"(failures: {self._failure_count})"
                )

        # HALF_OPEN에서 실패 시 다시 OPEN
        if self._state == "HALF_OPEN":
            self._state = "OPEN"
            logger.warning(
                f"🔴 CircuitBreaker[{self.name}]: HALF_OPEN -> OPEN (failure)"
            )

    def record_success(self):
        """성공 기록"""
        current_state = self.state  # 프로퍼티로 상태 갱신
        if current_state == "HALF_OPEN":
            # 반열림 상태에서 성공 시 회로 닫기
            self._state = "CLOSED"
            self._failure_count = 0
            self._success_count_in_half_open = 0
            logger.info(
                f"🟢 CircuitBreaker[{self.name}]: HALF_OPEN -> CLOSED (success)"
            )
        elif current_state == "CLOSED":
            # 정상 상태에서 성공 시 실패 카운트 리셋
            self._failure_count = 0

    def reset(self):
        """강제 리셋"""
        self._state = "CLOSED"
        self._failure_count = 0
        self._last_failure_time = 0
        self._success_count_in_half_open = 0
        logger.info(f"🔧 CircuitBreaker[{self.name}]: Reset to CLOSED")

    def get_status(self) -> dict:
        """상태 정보 반환"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
        }
