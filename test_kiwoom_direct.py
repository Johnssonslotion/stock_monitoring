#!/usr/bin/env python3
"""Kiwoom API 직접 호출 테스트"""
import asyncio
import httpx
import json
import os

async def main():
    # 환경변수에서 토큰 가져오기
    from redis.asyncio import Redis
    redis = await Redis.from_url("redis://deploy-redis:6379/15", decode_responses=True)
    
    token_data = await redis.get("api:token:kiwoom")
    if not token_data:
        print("❌ No Kiwoom token found")
        return
    
    token_info = json.loads(token_data)
    access_token = token_info["access_token"]
    
    print(f"✅ Token acquired: {access_token[:20]}...")
    
    # Kiwoom API 직접 호출
    async with httpx.AsyncClient(base_url="https://api.kiwoom.com", timeout=10.0) as client:
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {access_token}",
            "api-id": "ka10080",  # 매핑된 ID 사용
            "content-yn": "N",
            "User-Agent": "Mozilla/5.0"
        }
        
        body = {
            "stk_cd": "005930",
            "tic_scope": "1",
            "upd_stkpc_tp": "1"
        }
        
        print(f"\n📤 Request Headers:")
        print(json.dumps(headers, indent=2, ensure_ascii=False))
        print(f"\n📤 Request Body:")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        
        response = await client.post("/api/dostk/chart", headers=headers, json=body)
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"📥 Response Headers: {dict(response.headers)}")
        print(f"\n📥 Response Body:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    await redis.aclose()

asyncio.run(main())
