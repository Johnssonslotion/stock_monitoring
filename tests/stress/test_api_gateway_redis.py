"""
API Gateway Stress Test (Redis Backend)
Validates RedisRateLimiter (GateKeeper) effectiveness under high load.

SAFE: Uses Redis DB 1 to avoid affecting production data on DB 0.
"""

import asyncio
import time
import os
import sys
from collections import defaultdict

# Add project root to path
sys.path.insert(0, '/home/ubuntu/workspace/stock_backtest')

from src.api_gateway.rate_limiter import RedisRateLimiter

# Test Configuration
NUM_CLIENTS = 10     # Reduced for stability, but high frequency
REQUESTS_PER_CLIENT = 20
TARGET_RATE_LIMIT = 30  # calls/sec for KIS


class StressTestStats:
    def __init__(self, target_limit):
        self.target_limit = target_limit
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.request_times = []
        self.lock = asyncio.Lock()

    async def record(self, accepted):
        async with self.lock:
            now = time.time()
            self.total_requests += 1
            if accepted:
                self.accepted_requests += 1
                self.request_times.append(now)
            else:
                self.rejected_requests += 1

    def get_report(self):
        if not self.request_times:
            return "No requests made."
        
        duration = self.request_times[-1] - self.request_times[0]
        avg_rate = len(self.request_times) / duration if duration > 0 else 0
        
        # Calculate Peak Rate (per second bins)
        bins = defaultdict(int)
        for t in self.request_times:
            bins[int(t)] += 1
        peak_rate = max(bins.values()) if bins else 0
        
        report = [
            f"{'='*40}",
            f"📊 STRESS TEST REPORT (Redis DB 1)",
            f"{'='*40}",
            f"Total Requests: {self.total_requests}",
            f"Accepted:       {self.accepted_requests} ({self.accepted_requests/self.total_requests*100:.1f}%)",
            f"Rejected:       {self.rejected_requests}",
            f"Avg Rate:       {avg_rate:.2f} calls/sec",
            f"Peak Rate:      {peak_rate} calls/sec (Target: {self.target_limit})",
            f"Duration:       {duration:.2f}s",
            f"{'='*40}"
        ]
        
        if peak_rate <= self.target_limit * 1.1:
            report.append("✅ PASS: Rate limit strictly enforced.")
        else:
            report.append("❌ FAIL: Burst limit exceeded.")
            
        return "\n".join(report)


async def client_worker(client_id, limiter, stats):
    """Simulates a heavy API user"""
    for i in range(REQUESTS_PER_CLIENT):
        # Try to acquire token for 'KIS'
        # We don't wait here, we just see if it's allowed
        accepted = await limiter.acquire("KIS")
        await stats.record(accepted)
        
        # High frequency: 100ms delay between attempts
        await asyncio.sleep(0.05)


async def main():
    print(f"🚀 Starting Redis-backed Stress Test...")
    print(f"Target: KIS API ({TARGET_RATE_LIMIT} calls/sec)")
    
    # Initialize Limiter on DB 1 (Safe)
    limiter = RedisRateLimiter(db=1)
    await limiter.connect()
    
    # Reset Redis keys for clean test
    await limiter.redis.delete("rate_limit:KIS")
    
    stats = StressTestStats(TARGET_RATE_LIMIT)
    
    start_time = time.time()
    
    # Launch clients
    tasks = [
        client_worker(i, limiter, stats)
        for i in range(NUM_CLIENTS)
    ]
    
    await asyncio.gather(*tasks)
    
    print(stats.get_report())
    
    # Cleanup
    await limiter.redis.close()

if __name__ == "__main__":
    asyncio.run(main())
