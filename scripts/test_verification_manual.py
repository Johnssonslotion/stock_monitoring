#!/usr/bin/env python3
"""
Manual Verification Test Script
수동으로 검증 작업을 생성하고 결과를 모니터링합니다.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, '/app')

from src.verification.worker import VerificationProducer, VerificationTask


async def main():
    """수동 검증 작업 생성 및 모니터링"""
    
    # Producer 초기화
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/1")
    producer = VerificationProducer(redis_url)
    
    try:
        await producer.connect()
        print(f"✅ Producer connected to {redis_url}")
        
        # 테스트 종목: 삼성전자
        symbol = "005930"
        target_minute = (datetime.now() - timedelta(minutes=5)).replace(second=0, microsecond=0)
        
        # 검증 작업 생성
        task = VerificationTask(
            symbol=symbol,
            minute=target_minute.isoformat(),
            priority=False,
            mode="daily"
        )
        
        print(f"\n📋 Creating verification task:")
        print(f"  Symbol: {symbol}")
        print(f"  Minute: {target_minute.isoformat()}")
        print(f"  Mode: daily")
        
        # 작업을 큐에 추가
        await producer.produce_task(task)
        print(f"\n✅ Task added to queue")
        
        # 큐 상태 확인
        stats = await producer.get_queue_stats()
        print(f"\n📊 Queue Stats:")
        print(f"  Normal queue: {stats['normal']} tasks")
        print(f"  Priority queue: {stats['priority']} tasks")
        print(f"  DLQ: {stats['dlq']} tasks")
        
        print(f"\n💡 Task is now in the queue. Check verification-worker logs:")
        print(f"   docker logs verification-worker -f")
        
        # 10초 대기하여 처리 결과 확인
        print(f"\n⏳ Waiting 10 seconds for task processing...")
        await asyncio.sleep(10)
        
        # 처리 후 큐 상태 확인
        stats_after = await producer.get_queue_stats()
        print(f"\n📊 Queue Stats After Processing:")
        print(f"  Normal queue: {stats_after['normal']} tasks")
        print(f"  Priority queue: {stats_after['priority']} tasks")
        print(f"  DLQ: {stats_after['dlq']} tasks")
        
        if stats_after['normal'] < stats['normal']:
            print(f"\n✅ Task was processed!")
        else:
            print(f"\n⚠️  Task is still in queue. Check worker status.")
            
    finally:
        await producer.close()
        print(f"\n👋 Producer closed")


if __name__ == "__main__":
    asyncio.run(main())
