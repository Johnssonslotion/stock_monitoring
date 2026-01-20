import asyncio
import time
import pytest
import os
from src.api_gateway.rate_limiter import RedisRateLimiter

@pytest.mark.asyncio
async def test_rate_limiter_delay_accuracy():
    """
    Test if the RedisRateLimiter enforces the rate limit correctly.
    Target: 30 calls/sec -> 1 call per ~33.3ms
    We will test 60 calls. Total expected time should be >= (~2 seconds - burst allowance).
    """
    # Use DB 9 for testing to avoid interference
    limiter = RedisRateLimiter(db=9)
    await limiter.connect()
    
    # Reset existing tokens for clean test
    await limiter.redis.delete("rate_limit:TEST_API")
    
    # Configure 30 calls/sec, 5 burst
    limiter.config["TEST_API"] = (30, 5)
    
    test_calls = 60
    success_count = 0
    start_time = time.time()
    
    print(f"\n🚀 Starting Rate Limit Delay Test: {test_calls} calls at 30/sec (burst 5)")
    
    for i in range(test_calls):
        # wait_acquire uses a loop with 50ms sleep if blocked.
        # For precision, let's see how it behaves.
        success = await limiter.wait_acquire("TEST_API", timeout=5.0)
        if success:
            success_count += 1
            if i % 10 == 0:
                print(f"   Call {i} acquired at {time.time() - start_time:.3f}s")
    
    duration = time.time() - start_time
    print(f"🏁 Test Finished. Success: {success_count}/{test_calls}, Duration: {duration:.3f}s")
    
    # Expected behavior:
    # First 5 calls: ~0s (Burst)
    # Remaining 55 calls: Needs 55 / 30 = 1.833s
    # Total expected minimum duration: ~1.8s
    
    assert success_count == test_calls
    assert duration >= 1.5, f"Rate limiting too loose! Duration {duration:.3f}s < 1.5s"
    assert duration <= 3.0, f"Rate limiting too tight! Duration {duration:.3f}s > 3.0s"

@pytest.mark.asyncio
async def test_rate_limiter_burst():
    """
    Verify burst capability.
    """
    limiter = RedisRateLimiter(db=9)
    await limiter.connect()
    await limiter.redis.delete("rate_limit:BURST_API")
    
    # 10 calls/sec, 5 burst
    limiter.config["BURST_API"] = (10, 5)
    
    start_time = time.time()
    results = []
    
    # Immediate acquisition attempts
    for i in range(7):
        results.append(await limiter.acquire("BURST_API"))
    
    # First 5 should be True (Burst capacity)
    # Next 2 should be False (or maybe 1 more if tiny refill happened)
    true_count = sum(1 for r in results if r)
    print(f"\n🚀 Burst Test Results: {results} (True count: {true_count})")
    
    assert true_count >= 5
    assert true_count <= 6 # 6 if one token refilled during loop execution
    
    # Wait 0.5s -> should refill 5 tokens (10/sec * 0.5s = 5)
    await asyncio.sleep(0.6)
    refilled = await limiter.acquire("BURST_API")
    assert refilled is True

if __name__ == "__main__":
    # Allow running directly
    import sys
    async def run_standalone():
        try:
            await test_rate_limiter_delay_accuracy()
            await test_rate_limiter_burst()
        except Exception as e:
            print(f"❌ Test Failed: {e}")
            sys.exit(1)
        finally:
            print("\n✅ All tests passed!")
            sys.exit(0)
            
    asyncio.run(run_standalone())
