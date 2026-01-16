from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class BrokerBase(ABC):
    """
    모든 브로커(KIS, 키움, 미래)의 공통 인터페이스
    """
    def __init__(self, broker_name: str, config: Dict[str, Any]):
        self.broker_name = broker_name
        self.config = config
        self.is_running = False
        self.use_mock = config.get("use_mock", False)

    @abstractmethod
    async def connect(self) -> bool:
        """연결 및 세션 초기화"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """연결 종료"""
        pass

    @abstractmethod
    async def start_realtime_subscribe(self, symbols: List[str]) -> bool:
        """실시간 시세 구독 시작"""
        pass

    @abstractmethod
    async def stop_realtime_subscribe(self, symbols: List[str]) -> bool:
        """실시간 시세 구독 해제"""
        pass

    @abstractmethod
    async def send_order(self, symbol: str, quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
        """주문 전송 (매수/매도 공통)"""
        pass

    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """잔고/예수금 조회"""
        pass

    async def run(self):
        """메인 실행 루프"""
        self.is_running = True
        logger.info(f"🚀 Broker Worker Started: {self.broker_name} (Mock: {self.use_mock})")
        
        if not await self.connect():
            logger.error(f"❌ Failed to connect to {self.broker_name}")
            return

        try:
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info(f"🛑 Broker Worker Stopping: {self.broker_name}")
        finally:
            await self.disconnect()

class BrokerError(Exception):
    """브로커 관련 예외 처리"""
    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code
