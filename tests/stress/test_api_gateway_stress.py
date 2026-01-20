"""
Stress Test Environment for API Gateway

Simulates heavy concurrent load to verify Rate Limiter effectiveness.
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from collections import defaultdict

# Test Configuration
NUM_CLIENTS = 50
REQUESTS_PER_CLIENT = 20
TARGET_RATE_LIMIT = 20  # calls/sec


class MockAPIGateway:
    """
    Mock API Gateway with Rate Limiter
    (Redis 없이 in-memory로 테스트)
    """
    
    def __init__(self, rate_limit=20):
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
        
        # Metrics
        self.total_requests = 0
        self.accepted_requests = 0
        self.rejected_requests = 0
        self.request_times = []
    
    async def acquire(self):
        """Token Bucket Algorithm"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            
            # Refill tokens
            self.tokens = min(self.rate_limit, self.tokens + elapsed * self.rate_limit)
            self.last_refill = now
            
            # Try to acquire
            self.total_requests += 1
            
            if self.tokens >= 1:
                self.tokens -= 1
                self.accepted_requests += 1
                self.request_times.append(now)
                return True
            else:
                self.rejected_requests += 1
                return False
    
    def get_stats(self):
        """Calculate statistics"""
        if not self.request_times:
            return {}
        
        # Calculate actual rate
        duration = self.request_times[-1] - self.request_times[0]
        actual_rate = len(self.request_times) / duration if duration > 0 else 0
        
        # Time distribution
        time_bins = defaultdict(int)
        for t in self.request_times:
            second = int(t)
            time_bins[second] += 1
        
        peak_rate = max(time_bins.values()) if time_bins else 0
        
        return {
            'total': self.total_requests,
            'accepted': self.accepted_requests,
            'rejected': self.rejected_requests,
            'acceptance_rate': self.accepted_requests / self.total_requests * 100,
            'duration': duration,
            'avg_rate': actual_rate,
            'peak_rate': peak_rate,
            'target_exceeded': peak_rate > self.rate_limit
        }


async def client_worker(client_id, gateway, num_requests):
    """Simulate a client making requests"""
    results = []
    
    for i in range(num_requests):
        start = time.time()
        accepted = await gateway.acquire()
        latency = (time.time() - start) * 1000
        
        results.append({
            'client_id': client_id,
            'request_id': i,
            'accepted': accepted,
            'latency_ms': latency
        })
        
        # Small random delay to simulate real workload
        await asyncio.sleep(0.01 + (client_id % 5) * 0.01)
    
    return results


async def run_stress_test():
    """Run stress test"""
    print(f"\n{'='*60}")
    print(f"🧪 API Gateway Stress Test")
    print(f"{'='*60}")
    print(f"Clients: {NUM_CLIENTS}")
    print(f"Requests/Client: {REQUESTS_PER_CLIENT}")
    print(f"Total Requests: {NUM_CLIENTS * REQUESTS_PER_CLIENT}")
    print(f"Target Rate Limit: {TARGET_RATE_LIMIT} calls/sec")
    print(f"{'='*60}\n")
    
    # Create gateway
    gateway = MockAPIGateway(rate_limit=TARGET_RATE_LIMIT)
    
    # Launch clients
    print(f"🚀 Launching {NUM_CLIENTS} concurrent clients...")
    start_time = time.time()
    
    tasks = [
        client_worker(i, gateway, REQUESTS_PER_CLIENT)
        for i in range(NUM_CLIENTS)
    ]
    
    results = await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    
    # Flatten results
    all_results = [r for client_results in results for r in client_results]
    
    # Statistics
    stats = gateway.get_stats()
    
    print(f"\n{'='*60}")
    print(f"📊 TEST RESULTS")
    print(f"{'='*60}")
    print(f"Total Duration: {duration:.2f}s")
    print(f"Total Requests: {stats['total']}")
    print(f"Accepted: {stats['accepted']} ({stats['acceptance_rate']:.1f}%)")
    print(f"Rejected: {stats['rejected']}")
    print(f"\n📈 RATE STATISTICS:")
    print(f"Average Rate: {stats['avg_rate']:.2f} calls/sec")
    print(f"Peak Rate: {stats['peak_rate']} calls/sec")
    print(f"Target Rate: {TARGET_RATE_LIMIT} calls/sec")
    
    # Latency stats
    latencies = [r['latency_ms'] for r in all_results]
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    
    print(f"\n⏱️ LATENCY:")
    print(f"Average: {avg_latency:.2f}ms")
    print(f"P95: {p95_latency:.2f}ms")
    
    # Verdict
    print(f"\n{'='*60}")
    if stats['peak_rate'] <= TARGET_RATE_LIMIT * 1.1:  # 10% tolerance
        print(f"✅ PASS: Rate limit respected (Peak: {stats['peak_rate']} ≤ {TARGET_RATE_LIMIT})")
    else:
        print(f"❌ FAIL: Rate limit exceeded (Peak: {stats['peak_rate']} > {TARGET_RATE_LIMIT})")
    
    if avg_latency < 10:
        print(f"✅ PASS: Low latency (Avg: {avg_latency:.2f}ms < 10ms)")
    else:
        print(f"⚠️ WARNING: High latency (Avg: {avg_latency:.2f}ms)")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_stress_test())
