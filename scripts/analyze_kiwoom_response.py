import asyncio
import os
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(".env.backtest")

async def deep_analyze_kiwoom_response():
    """
    Deep analysis of Kiwoom API response
    Check headers, body, status code in detail
    """
    print("🔍 Deep Response Analysis - Kiwoom OAuth2 Token")
    print("="*80)
    
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    print(f"\n1️⃣ Environment Check:")
    print(f"   APP_KEY: {app_key}")
    print(f"   APP_SECRET: {app_secret[:10]}...{app_secret[-10:]}")
    
    # Test different token endpoints
    endpoints = [
        "https://api.kiwoom.com/oauth2/token",
        "https://mockapi.kiwoom.com/oauth2/token",
        "https://api.kiwoom.com/oauth2/tokenP",  # Try P variant like KIS
    ]
    
    for endpoint in endpoints:
        print(f"\n{'='*80}")
        print(f"Testing: {endpoint}")
        print(f"{'='*80}")
        
        payload = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret
        }
        
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, json=payload, headers=headers, ssl=False) as resp:
                    status = resp.status
                    
                    print(f"\n📥 Response:")
                    print(f"   Status Code: {status}")
                    print(f"   Reason: {resp.reason}")
                    
                    # Headers
                    print(f"\n   Response Headers:")
                    for key, value in resp.headers.items():
                        print(f"      {key}: {value}")
                    
                    # Body
                    try:
                        text = await resp.text()
                        print(f"\n   Body (raw):")
                        print(f"      {text[:500]}")
                        
                        # Try JSON
                        try:
                            data = json.loads(text)
                            print(f"\n   Body (JSON):")
                            print(json.dumps(data, indent=6, ensure_ascii=False))
                            
                            if status == 200:
                                print(f"\n   ✅ SUCCESS with {endpoint}!")
                                return data.get("token")
                        except:
                            print(f"\n   Body is not JSON")
                    except Exception as e:
                        print(f"   Error reading body: {e}")
                        
            except Exception as e:
                print(f"   ❌ Request failed: {e}")
    
    return None

if __name__ == "__main__":
    token = asyncio.run(deep_analyze_kiwoom_response())
    
    if token:
        print(f"\n{'='*80}")
        print(f"✅ Token obtained: {token[:30]}...")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"❌ All endpoints failed")
        print(f"{'='*80}")
