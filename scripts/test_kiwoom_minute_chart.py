import asyncio
import os
import aiohttp
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def test_kiwoom_minute_api(symbol="005930", tic_scope="1"):
    """
    Test Kiwoom ka10080 (주식분봉시세조회)
    Based on uploaded spec images
    """
    print(f"🔍 Testing Kiwoom ka10080 (Minute Chart) for {symbol}")
    print(f"   Tic Scope: {tic_scope}분")
    
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
            if resp.status != 200:
                print(f"  ❌ Token Error: {await resp.text()}")
                return False
            
            token_data = await resp.json()
            token = token_data.get("token")
            print(f"  ✅ Token obtained")
        
        # 2. Call ka10080 API
        api_url = "https://api.kiwoom.com/api/dostk/chart"
        
        api_headers = {
            "api-id": "ka10080",  # 주식분봉시세조회
            "authorization": f"Bearer {token}",
            "content-yn": "N",
            "Content-Type": "application/json; charset=UTF-8"
        }
        
        # Based on spec:
        # stk_cd: 종목코드
        # tic_scope: 틱범위 (1,3,5,10,15,30,45,60분)
        # upd_stakc_lp: 0 or 1
        api_payload = {
            "stk_cd": symbol,
            "tic_scope": tic_scope,
            "upd_stakc_lp": "1"  # Try 1 first
        }
        
        print(f"\n  📤 Request:")
        print(f"     URL: {api_url}")
        print(f"     API-ID: ka10080")
        print(f"     Body: {api_payload}")
        
        async with session.post(api_url, json=api_payload, headers=api_headers, ssl=False) as resp:
            print(f"\n  📥 Response Status: {resp.status}")
            
            if resp.status != 200:
                text = await resp.text()
                print(f"  ❌ API Error: {text[:500]}")
                return False
            
            data = await resp.json()
            print(f"\n  ✅ Response received!")
            
            # Check response structure
            if "stk_min_pols_chart_ary" in data:
                chart_data = data["stk_min_pols_chart_ary"]
                print(f"\n  📊 Found stk_min_pols_chart_ary with {len(chart_data)} items!")
                
                if len(chart_data) > 0:
                    print(f"\n  Sample data (first 3):")
                    for i, item in enumerate(chart_data[:3]):
                        print(f"    [{i}] {item}")
                    
                    # Save to CSV
                    df = pd.DataFrame(chart_data)
                    os.makedirs("data/proof", exist_ok=True)
                    filename = f"data/proof/kiwoom_minute_{symbol}_{tic_scope}min_{datetime.now().strftime('%Y%m%d')}.csv"
                    df.to_csv(filename, index=False)
                    print(f"\n  💾 Saved to: {filename}")
                    
                    return True
            else:
                print(f"  Response keys: {list(data.keys())}")
                print(f"  Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            return False

if __name__ == "__main__":
    # Test with 1-minute data
    result = asyncio.run(test_kiwoom_minute_api("005930", "1"))
    
    if result:
        print("\n✅ Kiwoom Minute API test SUCCESSFUL!")
        print("   → This API can retrieve minute chart data!")
    else:
        print("\n❌ Minute API test failed")
