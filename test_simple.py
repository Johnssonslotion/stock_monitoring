#!/usr/bin/env python3
"""간단한 API Hub 테스트"""
import asyncio
import json
from redis.asyncio import Redis

async def main():
    redis = await Redis.from_url("redis://localhost:6380/15", decode_responses=True)
    
    # KIS 태스크
    kis_task = {
        "task_id": "test_kis_live",
        "provider": "KIS",
        "tr_id": "FHKST01010100",
        "params": {"symbol": "005930"}
    }
    
    await redis.rpush("api:request:queue", json.dumps(kis_task))
    print(f"✅ Sent KIS task: {kis_task['task_id']}")
    
    # 결과 대기
    for i in range(10):
        await asyncio.sleep(1)
        result = await redis.get(f"api:response:{kis_task['task_id']}")
        if result:
            data = json.loads(result)
            print(f"\n✅ Got result after {i+1}s:")
            print(f"   Status: {data.get('status')}")
            if data.get('status') == 'SUCCESS':
                print(f"   Data length: {len(data.get('data', {}).get('data', []))}")
            else:
                print(f"   Reason: {data.get('reason')}")
            break
        print(f"⏳ Waiting... {i+1}/10")
    
    await redis.aclose()

asyncio.run(main())
