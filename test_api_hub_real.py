#!/usr/bin/env python3
"""
API Hub v2 실제 API 테스트 스크립트

실제 KIS/Kiwoom API를 호출하는 전체 워크플로우를 테스트합니다.
"""
import asyncio
import json
import os
from dotenv import load_dotenv
from redis.asyncio import Redis

# .env.prod 로드
load_dotenv(".env.prod")

async def test_api_hub_workflow():
    """API Hub 전체 워크플로우 테스트"""
    
    # Redis 연결 (API Hub는 DB 15 사용)
    redis_url = os.getenv("REDIS_URL_HUB", "redis://localhost:6379/15")
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    print(f"✅ Connected to Redis: {redis_url}")
    
    try:
        # 1. 기존 토큰 확인
        print("\n=== 1. 기존 토큰 확인 ===")
        kis_token = await redis.get("api:token:kis")
        kiwoom_token = await redis.get("api:token:kiwoom")
        
        if kis_token:
            kis_info = json.loads(kis_token)
            print(f"KIS Token: expires_at={kis_info.get('expires_at')}, refresh_count={kis_info.get('refresh_count', 0)}")
        else:
            print("KIS Token: Not found")
            
        if kiwoom_token:
            kiwoom_info = json.loads(kiwoom_token)
            print(f"Kiwoom Token: expires_at={kiwoom_info.get('expires_at')}, refresh_count={kiwoom_info.get('refresh_count', 0)}")
        else:
            print("Kiwoom Token: Not found")
        
        # 2. KIS API 호출 태스크 전송
        print("\n=== 2. KIS API 호출 태스크 전송 ===")
        kis_task = {
            "task_id": "test_kis_001",
            "provider": "KIS",
            "tr_id": "FHKST01010100",
            "params": {"symbol": "005930"},
            "priority": 5,
            "submitted_at": asyncio.get_event_loop().time()
        }
        
        await redis.rpush("api:request:queue", json.dumps(kis_task))
        print(f"✅ KIS Task submitted: {kis_task['task_id']}")
        
        # 3. Kiwoom API 호출 태스크 전송
        print("\n=== 3. Kiwoom API 호출 태스크 전송 ===")
        kiwoom_task = {
            "task_id": "test_kiwoom_001",
            "provider": "KIWOOM",
            "tr_id": "opt10081",
            "params": {"symbol": "005930"},
            "priority": 5,
            "submitted_at": asyncio.get_event_loop().time()
        }
        
        await redis.rpush("api:request:queue", json.dumps(kiwoom_task))
        print(f"✅ Kiwoom Task submitted: {kiwoom_task['task_id']}")
        
        # 4. 결과 대기 (최대 30초)
        print("\n=== 4. 결과 대기 (최대 30초) ===")
        
        for i in range(30):
            await asyncio.sleep(1)
            
            # KIS 결과 확인
            kis_result_key = f"api:response:{kis_task['task_id']}"
            kis_result = await redis.get(kis_result_key)
            
            if kis_result:
                result_data = json.loads(kis_result)
                print(f"\n✅ KIS 결과 수신 ({i+1}초 후):")
                print(f"   Status: {result_data.get('status')}")
                print(f"   Provider: {result_data.get('provider')}")
                print(f"   Data: {str(result_data.get('data', []))[:100]}...")
                kis_done = True
            else:
                kis_done = False
            
            # Kiwoom 결과 확인
            kiwoom_result_key = f"api:response:{kiwoom_task['task_id']}"
            kiwoom_result = await redis.get(kiwoom_result_key)
            
            if kiwoom_result:
                result_data = json.loads(kiwoom_result)
                print(f"\n✅ Kiwoom 결과 수신 ({i+1}초 후):")
                print(f"   Status: {result_data.get('status')}")
                print(f"   Provider: {result_data.get('provider')}")
                print(f"   Data: {str(result_data.get('data', []))[:100]}...")
                kiwoom_done = True
            else:
                kiwoom_done = False
            
            if kis_done and kiwoom_done:
                break
            
            if (i + 1) % 5 == 0:
                print(f"⏳ 대기 중... ({i+1}/30초)")
        
        # 5. 최종 토큰 상태 확인
        print("\n=== 5. 최종 토큰 상태 확인 ===")
        kis_token_after = await redis.get("api:token:kis")
        kiwoom_token_after = await redis.get("api:token:kiwoom")
        
        if kis_token_after:
            kis_info = json.loads(kis_token_after)
            print(f"KIS Token: expires_at={kis_info.get('expires_at')}, refresh_count={kis_info.get('refresh_count', 0)}")
        
        if kiwoom_token_after:
            kiwoom_info = json.loads(kiwoom_token_after)
            print(f"Kiwoom Token: expires_at={kiwoom_info.get('expires_at')}, refresh_count={kiwoom_info.get('refresh_count', 0)}")
        
        # 6. 큐 상태 확인
        print("\n=== 6. 큐 상태 확인 ===")
        pending_count = await redis.llen("api:request:queue")
        print(f"Request Queue: {pending_count} tasks")
        
        print("\n✅ 테스트 완료!")
        
    finally:
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(test_api_hub_workflow())
