import asyncio
import json
import uuid
import os
from redis.asyncio import Redis

async def test_hub_task():
    # Redis 접속 (DB 15)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/15")
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "provider": "KIS",
        "tr_id": "FHKST01010100",  # 주식현재가 시세
        "params": {"symbol": "005930"}, # 삼성전자
    }
    
    print(f"🚀 Pushing task {task_id} to api:request:queue...")
    await redis.lpush("api:request:queue", json.dumps(task))
    
    # 결과 대기 (최대 10초)
    print("⏳ Waiting for response...")
    for _ in range(20):
        resp_json = await redis.get(f"api:response:{task_id}")
        if resp_json:
            result = json.loads(resp_json)
            print("✅ Response Received:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            break
        await asyncio.sleep(0.5)
    else:
        print("❌ Timeout waiting for response")
        
    await redis.close()

if __name__ == "__main__":
    asyncio.run(test_hub_task())
