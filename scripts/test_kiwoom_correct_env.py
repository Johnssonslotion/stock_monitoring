import asyncio
import os
import aiohttp
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# CRITICAL: Use .env.backtest as specified
load_dotenv(".env.backtest")

async def test_kiwoom_with_correct_env(symbol="005930", tic_scope="1"):
    """
    Test Kiwoom ka10080 with CORRECT environment variables
    """
    print(f"🔍 Testing Kiwoom ka10080 (Minute Chart)")
    print(f"   Symbol: {symbol}, Tic Scope: {tic_scope}분")
    
    # Verify environment variables
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    if not app_key or not app_secret:
        print(f"  ❌ Environment variables not loaded!")
        print(f"     KIWOOM_APP_KEY exists: {bool(app_key)}")
        print(f"     KIWOOM_APP_SECRET exists: {bool(app_secret)}")
        return False
    
    print(f"  ✅ Keys loaded from .env.backtest")
    print(f"     APP_KEY: {app_key[:10]}...")
    
    # 1. Get Token
    token_url = "https://api.kiwoom.com/oauth2/token"
    token_payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    token_headers = {
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    async with aiohttp.ClientSession() as session:
        print(f"\n  📤 Requesting token...")
        async with session.post(token_url, json=token_payload, headers=token_headers, ssl=False) as resp:
            print(f"     Status: {resp.status}")
            
            if resp.status != 200:
                print(f"  ❌ Token Error: {await resp.text()}")
                return False
            
            token_data = await resp.json()
            token = token_data.get("token")
            print(f"  ✅ Token obtained: {token[:20]}...")
        
        # 2. Call ka10080 API - Try EXACTLY as spec shows
        api_url = "https://api.kiwoom.com/api/dostk/chart"
        
        # EXACT headers from spec
        api_headers = {
            "api-id": "ka10080",
            "authorization": f"Bearer {token}",
            "content-yn": "N",  # From spec
            "Content-Type": "application/json;charset=UTF-8"  # EXACT match
        }
        
        # Body from spec
        api_payload = {
            "stk_cd": symbol,
            "tic_scope": tic_scope,
            "upd_stakc_lp": "1"
        }
        
        print(f"\n  📤 Calling ka10080...")
        print(f"     URL: {api_url}")
        print(f"     Headers: {json.dumps(api_headers, indent=6)}")
        print(f"     Body: {json.dumps(api_payload, indent=6)}")
        
        async with session.post(api_url, json=api_payload, headers=api_headers, ssl=False) as resp:
            status = resp.status
            print(f"\n  📥 Response Status: {status}")
            
            text = await resp.text()
            
            if status != 200:
                print(f"  ❌ Error Response:")
                print(f"     {text[:800]}")
                
                # Also try to parse as JSON
                try:
                    error_json = json.loads(text)
                    print(f"\n  Error JSON: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                except:
                    pass
                
                return False
            
            # Success!
            data = json.loads(text)
            print(f"  ✅ SUCCESS!")
            print(f"\n  Response keys: {list(data.keys())}")
            
            if "stk_min_pols_chart_ary" in data:
                chart_data = data["stk_min_pols_chart_ary"]
                print(f"\n  📊 Found minute chart data: {len(chart_data)} items")
                
                if len(chart_data) > 0:
                    print(f"\n  Sample (first 3):")
                    for i, item in enumerate(chart_data[:3]):
                        print(f"    {i+1}. {item}")
                    
                    # Save
                    df = pd.DataFrame(chart_data)
                    os.makedirs("data/proof", exist_ok=True)
                    filename = f"data/proof/kiwoom_minute_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(filename, index=False)
                    print(f"\n  💾 Saved to: {filename}")
                    
                    return True
            else:
                print(f"\n  Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            return False

if __name__ == "__main__":
    result = asyncio.run(test_kiwoom_with_correct_env("005930", "1"))
    
    if result:
        print("\n" + "="*80)
        print("✅ Kiwoom Minute API WORKS!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("❌ Still failing - need to debug further")
        print("="*80)
