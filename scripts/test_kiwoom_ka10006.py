import asyncio
import os
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def test_kiwoom_ka10006(symbol="005930", target_date="20260101"):
    """
    Test Kiwoom REST API ka10006 (주식시세조회)
    Based on uploaded spec image
    """
    print(f"🔍 Testing Kiwoom ka10006 API for {symbol} on {target_date}")
    
    # 1. Get Token
    token_url = "https://api.kiwoom.com/oauth2/token"
    token_payload = {
        "grant_type": "client_credentials",
        "appkey": os.getenv("KIWOOM_APP_KEY"),
        "secretkey": os.getenv("KIWOOM_APP_SECRET")
    }
    token_headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    
    async with aiohttp.ClientSession() as session:
        # Get Token
        async with session.post(token_url, json=token_payload, headers=token_headers, ssl=False) as resp:
            print(f"  Token Request Status: {resp.status}")
            if resp.status != 200:
                text = await resp.text()
                print(f"  ❌ Token Error: {text}")
                return False
            
            token_data = await resp.json()
            token = token_data.get("token")
            if not token:
                print(f"  ❌ No token in response")
                return False
            
            print(f"  ✅ Token obtained: {token[:20]}...")
        
        # 2. Call ka10006 API
        api_url = "https://api.kiwoom.com/api/dostk/mrkcond"
        
        # Based on spec image:
        # Header: api-id, authorization, content-yn, next-key
        # Body: stk_cd
        api_headers = {
            "api-id": "ka10006",
            "authorization": f"Bearer {token}",
            "content-yn": "N",  # or "Y"?
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        # Try with just stk_cd
        api_payload = {
            "stk_cd": symbol
        }
        
        print(f"\n  📤 Request to ka10006:")
        print(f"     URL: {api_url}")
        print(f"     Headers: {api_headers}")
        print(f"     Body: {api_payload}")
        
        async with session.post(api_url, json=api_payload, headers=api_headers, ssl=False) as resp:
            print(f"\n  📥 Response Status: {resp.status}")
            
            if resp.status != 200:
                text = await resp.text()
                print(f"  ❌ API Error: {text}")
                return False
            
            data = await resp.json()
            print(f"\n  ✅ Response Data:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Analyze response structure
            if isinstance(data, list):
                print(f"\n  📊 Response is a LIST with {len(data)} items")
                if len(data) > 0:
                    print(f"  Sample item keys: {list(data[0].keys())}")
                    return True
            elif isinstance(data, dict):
                print(f"\n  📊 Response is a DICT")
                print(f"  Keys: {list(data.keys())}")
                
                # Check if it contains list of candles
                for key in ['output', 'data', 'result']:
                    if key in data and isinstance(data[key], list):
                        print(f"  → Found list in '{key}' with {len(data[key])} items")
                        return True
            
            return False

if __name__ == "__main__":
    result = asyncio.run(test_kiwoom_ka10006("005930", "20260101"))
    if result:
        print("\n✅ Kiwoom ka10006 API test SUCCESSFUL!")
    else:
        print("\n⚠️ Need more information about ka10006 API usage")
