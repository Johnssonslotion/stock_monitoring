import asyncio
import json
import time
import uuid
import logging
import aiohttp
from typing import Dict, Any, Optional
from redis.asyncio import Redis
from src.api_gateway.rate_limiter import RedisRateLimiter

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GatewayWorker")

class GatewayWorker:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[Redis] = None
        self.limiter: Optional[RedisRateLimiter] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        
        # Priority Queues
        self.queues = ["api:queue:0", "api:queue:1", "api:queue:2"] # High, Normal, Low
        
        # Pause status for 429 management
        self.pause_until = {"KIS": 0, "KIWOOM": 0}

    async def connect(self):
        self.redis = await Redis.from_url(self.redis_url, decode_responses=True)
        self.limiter = RedisRateLimiter(self.redis_url)
        self.session = aiohttp.ClientSession()
        logger.info(f"✅ Gateway Worker connected to Redis: {self.redis_url}")

    async def run(self):
        if not self.redis:
            await self.connect()
        
        self.is_running = True
        logger.info("🚀 Unified Gateway Worker Started...")
        
        while self.is_running:
            try:
                # 1. Fetch Request (Prioritized)
                # BLPOP returns (queue_name, data)
                result = await self.redis.blpop(self.queues, timeout=1)
                if not result:
                    continue
                
                queue_name, raw_data = result
                req = json.loads(raw_data)
                req_id = req.get("id", str(uuid.uuid4()))
                api_name = req.get("api", "KIS").upper()
                
                # 2. Dispatched Execution
                asyncio.create_task(self.handle_request(api_name, req))
                
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")
                await asyncio.sleep(1)

    async def handle_request(self, api_name: str, req: Dict[str, Any]):
        req_id = req.get("id")
        
        # 1. Check Circuit Breaker (Pause)
        now = time.time()
        if now < self.pause_until.get(api_name, 0):
            # Put back to queue or handle delay
            logger.warning(f"⚠️ {api_name} is paused. Re-queueing request {req_id}")
            await self.redis.rpush(self.queues[1], json.dumps(req))
            return

        # 2. Wait for Token
        allowed = False
        while not allowed:
            allowed = await self.limiter.is_allowed(api_name)
            if not allowed:
                # Calculate sleep based on rate (e.g., 30 calls/sec -> ~33ms)
                await asyncio.sleep(0.01)

        # 3. Execute Call
        result = await self.execute_call(api_name, req)
        
        # 4. Handle Response & 429
        status = result.get("status")
        if status == 429:
            logger.error(f"🚨 {api_name} Rate Limited (429). Pausing for 5 seconds.")
            self.pause_until[api_name] = time.time() + 5
            # Put back to queue
            await self.redis.rpush(self.queues[0], json.dumps(req)) # High priority for retries
            return

        # 5. Publish Result
        response_key = f"api:response:{req_id}"
        await self.redis.set(response_key, json.dumps(result), ex=60)
        await self.redis.publish(f"api:topic:{req_id}", json.dumps(result))

    async def execute_call(self, api_name: str, req: Dict[str, Any]) -> Dict[str, Any]:
        """Actual API Call Implementation (Stubs for now)"""
        endpoint = req.get("endpoint")
        method = req.get("method", "GET").upper()
        params = req.get("params", {})
        headers = req.get("headers", {})
        
        # TODO: Add real KIS/Kiwoom credentials and logic
        start = time.time()
        try:
            # Mock Call for now
            # In real case, we use self.session.request(...)
            latency = (time.time() - start) * 1000
            return {
                "id": req.get("id"),
                "status": 200,
                "data": {"mock": "data"},
                "latency_ms": latency,
                "api": api_name
            }
        except Exception as e:
            return {"id": req.get("id"), "status": 500, "error": str(e)}

    async def stop(self):
        self.is_running = False
        if self.session:
            await self.session.close()
        if self.redis:
            await self.redis.close()

if __name__ == "__main__":
    import os
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    worker = GatewayWorker(REDIS_URL)
    asyncio.run(worker.run())
