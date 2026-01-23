"""
REST API Worker (Mock Mode Only)

운영 환경 충돌 방지를 위해 Mock Client만 사용합니다.
실제 API 호출은 Phase 2에서 구현됩니다.

역할:
- Redis 큐에서 태스크를 상시 리스닝 (blpop)
- 우선순위 큐 선처리 (api:priority:queue > api:request:queue)
- TaskDispatcher를 통한 Mock 실행
- Circuit Breaker 및 Rate Limiter 통합
"""
import asyncio
import logging
import json
import os
import signal
from typing import Optional

from .queue import QueueManager, PRIORITY_QUEUE, NORMAL_QUEUE
from .dispatcher import TaskDispatcher
from .circuit_breaker import CircuitBreaker

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logger = logging.getLogger("RestApiWorker")


class MockClient:
    """
    Mock API Client (Phase 1)
    
    실제 KIS/Kiwoom API를 호출하지 않고,
    샘플 데이터를 반환합니다.
    """
    
    def __init__(self, provider: str):
        self.provider = provider
        logger.info(f"🎭 MockClient initialized for {provider}")
    
    async def execute(self, tr_id: str, params: dict) -> dict:
        """Mock API 실행"""
        await asyncio.sleep(0.1)  # 네트워크 지연 시뮬레이션
        
        logger.info(f"🎭 Mock API Call: {self.provider} {tr_id} {params}")
        
        # 샘플 데이터 반환
        return {
            "provider": self.provider,
            "tr_id": tr_id,
            "params": params,
            "result": "SUCCESS",
            "data": {
                "symbol": params.get("symbol", "TEST"),
                "timestamp": "2026-01-23T00:00:00Z",
                "candles": []
            }
        }


class RestApiWorker:
    """
    REST API Worker (Main Daemon)
    
    Mock 모드로만 동작하며, 운영 환경과 격리됩니다.
    """
    
    def __init__(
        self,
        redis_url: str = None,
        enable_mock: bool = True
    ):
        """
        Args:
            redis_url: Redis 연결 URL (기본값: 환경변수 또는 localhost)
            enable_mock: Mock 모드 강제 활성화 (Phase 1)
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", 
            "redis://localhost:6379/0"
        )
        self.enable_mock = enable_mock
        self.is_running = False
        
        # 컴포넌트 초기화
        self.queue_manager: Optional[QueueManager] = None
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            name="api-hub"
        )
        self.dispatcher: Optional[TaskDispatcher] = None
        
        logger.info(f"🚀 RestApiWorker initialized (Mock Mode: {enable_mock})")
    
    async def setup(self):
        """컴포넌트 초기화 및 연결"""
        # Queue Manager 초기화
        self.queue_manager = QueueManager(redis_url=self.redis_url)
        await self.queue_manager.connect()
        
        # Mock Clients 등록
        mock_kis = MockClient("KIS")
        mock_kiwoom = MockClient("KIWOOM")
        
        # Dispatcher 초기화
        self.dispatcher = TaskDispatcher(
            circuit_breaker=self.circuit_breaker,
            clients={
                "KIS": mock_kis,
                "KIWOOM": mock_kiwoom
            }
        )
        
        logger.info("✅ RestApiWorker setup completed")
    
    async def process_task(self, task: dict):
        """
        단일 태스크 처리
        
        Args:
            task: 큐에서 pop한 태스크
        """
        task_id = task.get("task_id", "unknown")
        provider = task.get("provider", "unknown")
        
        logger.info(f"📥 Processing task: {task_id} (provider: {provider})")
        
        # Dispatcher로 실행
        result = await self.dispatcher.dispatch(task)
        
        status = result.get("status")
        if status == "SUCCESS":
            logger.info(f"✅ Task {task_id} completed successfully")
        elif status == "REJECTED":
            reason = result.get("reason")
            logger.warning(f"⛔ Task {task_id} rejected: {reason}")
        elif status == "ERROR":
            error = result.get("reason")
            logger.error(f"❌ Task {task_id} failed: {error}")
        
        return result
    
    async def run(self):
        """
        메인 이벤트 루프
        
        Redis 큐를 상시 리스닝하며, 태스크를 순차적으로 처리합니다.
        우선순위: PRIORITY_QUEUE > NORMAL_QUEUE
        """
        await self.setup()
        
        self.is_running = True
        logger.info("🟢 RestApiWorker started (Mock Mode)")
        
        try:
            while self.is_running:
                # blpop: 우선순위 큐 먼저, 타임아웃 1초
                result = await self.queue_manager.redis.blpop(
                    [PRIORITY_QUEUE, NORMAL_QUEUE],
                    timeout=1
                )
                
                if result is None:
                    # 타임아웃, 계속 대기
                    continue
                
                queue_key, task_json = result
                
                try:
                    task = json.loads(task_json)
                    await self.process_task(task)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid task JSON: {e}")
                except Exception as e:
                    logger.error(f"❌ Task processing error: {e}", exc_info=True)
        
        except asyncio.CancelledError:
            logger.info("🛑 RestApiWorker cancelled")
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """리소스 정리"""
        self.is_running = False
        
        if self.queue_manager and self.queue_manager.redis:
            await self.queue_manager.redis.aclose()
        
        logger.info("🔴 RestApiWorker stopped")
    
    def stop(self):
        """Worker 중지 (외부 호출용)"""
        logger.info("🛑 Stop signal received")
        self.is_running = False


async def main():
    """엔트리포인트"""
    worker = RestApiWorker()
    
    # Signal 핸들러 등록 (Graceful Shutdown)
    def signal_handler(sig, frame):
        logger.info(f"📡 Received signal: {sig}")
        worker.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Worker 실행
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
