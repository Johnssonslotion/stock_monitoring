import asyncio
import logging
import json
import random
from typing import Dict, Any, List, Optional
from src.trading.broker_base import BrokerBase, BrokerError
from src.data_ingestion.price.schemas.kiwoom_re import KiwoomRealData, KiwoomLoginResponse
from src.data_ingestion.price.common.mock_provider import mock_stream_producer
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class KiwoomREAdapter(BrokerBase):
    """
    키움 Open API RE용 어댑터 (Linux Native)
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__("kiwoom_re", config)
        self.redis_client = None
        self.mock_queue = asyncio.Queue()
        self.mock_task = None

    async def connect(self) -> bool:
        self.redis_client = await redis.from_url(self.config.get("redis_url", "redis://localhost:6379/0"))
        
        if self.use_mock:
            logger.info("🎭 Kiwoom RE Adapter: Running in MOCK mode")
            return True

        # 실제 로그인 및 세션 확인 로직 (추후 구현)
        return False

    async def disconnect(self) -> None:
        if self.mock_task:
            self.mock_task.cancel()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("🔌 Kiwoom RE Adapter: Disconnected")

    async def start_realtime_subscribe(self, symbols: List[str]) -> bool:
        if self.use_mock:
            self.mock_task = asyncio.create_task(
                mock_stream_producer(self.mock_queue, "kiwoom_re", symbols)
            )
            asyncio.create_task(self._mock_consumer_loop())
            return True
        return False

    async def _mock_consumer_loop(self):
        while True:
            data = await self.mock_queue.get()
            try:
                # FID 기반 스키마 검증
                validated = KiwoomRealData(**data)
                channel = f"ticker.{self.broker_name}"
                msg = {
                    "symbol": validated.symbol,
                    "price": validated.price,
                    "volume": validated.volume,
                    "change": validated.change,
                    "time": validated.time,
                    "broker": self.broker_name,
                    "is_mock": True
                }
                await self.redis_client.publish(channel, json.dumps(msg))
                logger.debug(f"📤 Kiwoom RE Mock Published: {validated.symbol} @ {validated.price}")
            except Exception as e:
                logger.error(f"Kiwoom RE Mock Consumer Error: {e}")
            finally:
                self.mock_queue.task_done()

    async def stop_realtime_subscribe(self, symbols: List[str]) -> bool:
        if self.mock_task:
            self.mock_task.cancel()
        return True

    async def send_order(self, symbol: str, quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
        if self.use_mock:
            return {"status": "success", "order_id": f"kiwoom_mock_{random.randint(1000, 9999)}"}
        return {"status": "error", "msg": "Real order not supported in Phase 1"}

    async def get_balance(self) -> Dict[str, Any]:
        if self.use_mock:
            return {"cash": 50000000, "stocks": {}}
        return {"error": "Not implemented"}
