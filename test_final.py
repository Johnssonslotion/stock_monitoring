#!/usr/bin/env python3
"""최종 API Hub 통합 테스트"""
import asyncio
import json
from redis.asyncio import Redis

async def main():
    redis = await Redis.from_url("redis://localhost:6380/15", decode_responses=True)
    
    print("🚀 API Hub v2 Phase 3 - Real API Integration Test\n")
    
    # 1. 토큰 상태 확인
    print("=== 1. Token Status ===")
    kis_token = await redis.get("api:token:kis")
    kiwoom_token = await redis.get("api:token:kiwoom")
    
    if kis_token:
        info = json.loads(kis_token)
        print(f"✅ KIS Token: refresh_count={info.get('refresh_count', 0)}")
    else:
        print("❌ KIS Token: Not found")
    
    if kiwoom_token:
        info = json.loads(kiwoom_token)
        print(f"✅ Kiwoom Token: refresh_count={info.get('refresh_count', 0)}")
    else:
        print("❌ Kiwoom Token: Not found")
    
    # 2. KIS API 테스트
    print("\n=== 2. KIS API Test (Samsung Electronics) ===")
    kis_task = {
        "task_id": "final_test_kis",
        "provider": "KIS",
        "tr_id": "FHKST01010100",
        "params": {"symbol": "005930"}
    }
    await redis.rpush("api:request:queue", json.dumps(kis_task))
    print(f"📤 Task submitted: {kis_task['task_id']}")
    
    for i in range(10):
        await asyncio.sleep(1)
        result = await redis.get(f"api:response:{kis_task['task_id']}")
        if result:
            data = json.loads(result)
            if data.get('status') == 'SUCCESS':
                print(f"✅ SUCCESS after {i+1}s")
                print(f"   Data records: {len(data.get('data', {}).get('data', []))}")
            else:
                print(f"❌ FAILED: {data.get('reason')}")
            break
    
    # 3. Kiwoom API 테스트
    print("\n=== 3. Kiwoom API Test (Samsung Electronics) ===")
    kiwoom_task = {
        "task_id": "final_test_kiwoom",
        "provider": "KIWOOM",
        "tr_id": "opt10081",
        "params": {"symbol": "005930"}
    }
    await redis.rpush("api:request:queue", json.dumps(kiwoom_task))
    print(f"📤 Task submitted: {kiwoom_task['task_id']}")
    
    for i in range(10):
        await asyncio.sleep(1)
        result = await redis.get(f"api:response:{kiwoom_task['task_id']}")
        if result:
            data = json.loads(result)
            if data.get('status') == 'SUCCESS':
                print(f"✅ SUCCESS after {i+1}s")
                print(f"   Data records: {len(data.get('data', {}).get('data', []))}")
            else:
                print(f"❌ FAILED: {data.get('reason')}")
            break
    
    # 4. 최종 상태
    print("\n=== 4. Final Status ===")
    queue_len = await redis.llen("api:request:queue")
    print(f"Queue length: {queue_len}")
    
    print("\n🎉 Integration test completed!")
    await redis.aclose()

asyncio.run(main())
