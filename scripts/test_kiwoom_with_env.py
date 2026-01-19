import asyncio
import os
import aiohttp
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Use .env (NOT .env.backtest)
load_dotenv()

async def test_with_correct_key(symbol="005930", tic_scope="1"):
    """
    Test with .env keys (which WebSocket uses successfully)
    """
    print(f"🔍 Testing Kiwoom ka10080 with .env keys")
    
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    print(f"   APP_KEY: {app_key}")
    
    # 1. Get Token
    token_url = "https://api.kiwoom.com/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    
    async with aiohttp.ClientSession() as session:
        print(f"\n📤 Requesting token...")
        async with session.post(token_url, json=payload, headers=headers, ssl=False) as resp:
            print(f"   Status: {resp.status}")
            
            data = await resp.json()
            print(f"   Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get("return_code") != 0:
                print(f"  ❌ Token failed: {data.get('return_msg')}")
                return False
            
            token = data.get("token")
            print(f"  ✅ Token: {token[:30]}...")
        
        # 2. Call ka10080
        api_url = "https://api.kiwoom.com/api/dostk/chart"
        api_headers = {
            "api-id": "ka10080",
            "authorization": f"Bearer {token}",
            "content-yn": "N",
            "Content-Type": "application/json;charset=UTF-8"
        }
        api_payload = {
            "stk_cd": symbol,
            "tic_scope": tic_scope,
            "upd_stakc_lp": "1"
        }
        
        print(f"\n📤 Calling ka10080...")
        async with session.post(api_url, json=api_payload, headers=api_headers, ssl=False) as resp:
            print(f"   Status: {resp.status}")
            
            text = await resp.text()
            
            if resp.status != 200:
                print(f"  ❌ Error: {text[:500]}")
                return False
            
            data = json.loads(text)
            print(f"  ✅ Response received!")
            
            if "stk_min_pols_chart_ary" in data:
                chart_data = data["stk_min_pols_chart_ary"]
                print(f"\n📊 Minute chart data: {len(chart_data)} items")
                
                if len(chart_data) > 0:
                    print(f"\nSample (first 3):")
                    for i, item in enumerate(chart_data[:3]):
                        print(f"  {i+1}. {item}")
                    
                    df = pd.DataFrame(chart_data)
                    os.makedirs("data/proof", exist_ok=True)
                    filename = f"data/proof/kiwoom_minute_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(filename, index=False)
                    print(f"\n💾 Saved: {filename}")
                    
                    return True
            
            print(f"Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_with_correct_key("005930", "1"))
    
    if result:
        print("\n" + "="*80)
        print("✅ Kiwoom Minute API WORKS WITH CORRECT KEY!")
        print("="*80)
