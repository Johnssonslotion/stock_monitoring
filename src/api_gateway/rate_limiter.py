import asyncio
import time
import os
import json
import redis.asyncio as redis
from datetime import datetime

class RedisRateLimiter:
    """
    Distributed Rate Limiter using Redis (Token Bucket Algorithm)
    Targeted for KIS/Kiwoom API Gateway.
    
    [Council 2차 결정] 물리적으로 분리된 redis-gatekeeper 컨테이너 사용
    """
    def __init__(self, redis_url=None):
        # Council 2차 결정: 물리적 분리를 위해 전용 REDIS_URL_GATEKEEPER 사용
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL_GATEKEEPER", 
            os.getenv("REDIS_URL", "redis://localhost:6379/0")
        )
        
        self.redis = None
        # {API_NAME: (Rate, Capacity)}
        # Ground Truth Policy 섹션 8.1 준수
        self.config = {
            "KIS": (20, 5),     # 20 calls/sec, max 5 burst (KIS 공식 제한)
            "KIWOOM": (10, 3)   # 10 calls/sec, max 3 burst (Kiwoom 공식 제한)
        }

    async def connect(self):
        if not self.redis:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            print(f"✅ Rate Limiter connected to Redis: {self.redis_url}")

    async def acquire(self, api_name: str, priority: int = 2) -> bool:
        """
        Try to acquire a token for the specified API.
        Implementation using Lua script for atomicity.
        """
        if not self.redis:
            await self.connect()

        rate, capacity = self.config.get(api_name, (10, 2))
        key = f"rate_limit:{api_name}"
        
        # Lua script for Token Bucket
        # KEYS[1]: rate limit key
        # ARGV[1]: limit (capacity)
        # ARGV[2]: refill rate (per sec)
        # ARGV[3]: now (timestamp)
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        
        local bucket = redis.call("HMGET", key, "tokens", "last_refill")
        local tokens = tonumber(bucket[1]) or limit
        local last_refill = tonumber(bucket[2]) or now
        
        -- Refill tokens
        local elapsed = math.max(0, now - last_refill)
        tokens = math.min(limit, tokens + (elapsed * rate))
        
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
            return 1
        else
            return 0
        end
        """
        
        try:
            now = time.time()
            # ARGV[1]: capacity, ARGV[2]: refill rate
            result = await self.redis.eval(lua_script, 1, key, capacity, rate, now)
            return bool(result)
        except Exception as e:
            print(f"❌ Rate Limiter Error: {e}")
            # Fallback: Allow on error to avoid system halt
            return True

    async def wait_acquire(self, api_name: str, timeout: float = 5.0) -> bool:
        """Wait until a token is available or timeout"""
        start = time.time()
        while time.time() - start < timeout:
            if await self.acquire(api_name):
                return True
            await asyncio.sleep(0.05) # Check every 50ms
        return False

# Global instance for reuse
gatekeeper = RedisRateLimiter()
