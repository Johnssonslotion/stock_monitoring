import asyncio
import logging
from typing import Dict, List, Any, Type
from src.trading.broker_base import BrokerBase
from src.trading.adapters.mirae import MiraeAdapter
from src.trading.adapters.kiwoom_re import KiwoomREAdapter

logger = logging.getLogger(__name__)

class BrokerOrchestrator:
    """
    여러 브로커 워커를 가변적으로 관리하는 오케스트레이터
    """
    ADAPTER_MAP: Dict[str, Type[BrokerBase]] = {
        "mirae": MiraeAdapter,
        "kiwoom_re": KiwoomREAdapter
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_brokers: Dict[str, BrokerBase] = {}
        self.tasks: List[asyncio.Task] = []

    def setup_brokers(self, broker_names: List[str]):
        """설정에 따라 브로커 인스턴스 생성"""
        for name in broker_names:
            if name in self.ADAPTER_MAP:
                adapter_cls = self.ADAPTER_MAP[name]
                # 브로커별 개별 설정 추출 (없으면 기본값)
                broker_config = self.config.get("brokers", {}).get(name, {})
                broker_config.update({
                    "redis_url": self.config.get("redis_url"),
                    "use_mock": self.config.get("use_mock", False)
                })
                
                self.active_brokers[name] = adapter_cls(broker_config)
                logger.info(f"🆕 Broker Setup: {name}")
            else:
                logger.warning(f"⚠️ Unknown broker requested: {name}")

    async def start_all(self, symbols: Dict[str, List[str]]):
        """본격적인 수집 및 워커 루프 시작"""
        if not self.active_brokers:
            logger.error("❌ No active brokers to start")
            return

        for name, broker in self.active_brokers.items():
            # 1. Connect
            if await broker.connect():
                # 2. Start Realtime Subscription
                broker_symbols = symbols.get(name, [])
                if await broker.start_realtime_subscribe(broker_symbols):
                    # 3. Add to Task list
                    self.tasks.append(asyncio.create_task(broker.run()))
                    logger.info(f"✅ Broker {name} is running")
            else:
                logger.error(f"❌ Failed to connect broker: {name}")

    async def stop_all(self):
        """모든 워커 중지"""
        for name, broker in self.active_brokers.items():
            broker.is_running = False
            await broker.disconnect()
        
        for task in self.tasks:
            task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("🛑 All brokers stopped")
