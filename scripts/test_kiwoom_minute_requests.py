import os
import requests
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_kiwoom_minute_api(symbol="005930", tic_scope="1"):
    """
    Test Kiwoom ka10080 (Minute Chart) using requests library
    """
    print(f"🔍 Testing Kiwoom ka10080 (Minute Chart)")
    print(f"   Symbol: {symbol}, Tic Scope: {tic_scope}분")
    print("="*80)
    
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    # 1. Get Token
    print(f"\n1️⃣ Getting token...")
    token_url = "https://api.kiwoom.com/oauth2/token"
    token_payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    token_headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    
    resp = requests.post(token_url, json=token_payload, headers=token_headers, verify=False)
    print(f"   Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"   ❌ Token Error: {resp.text[:500]}")
        return False
    
    token_data = resp.json()
    if token_data.get("return_code") != 0:
        print(f"   ❌ API Error: {token_data.get('return_msg')}")
        return False
    
    token = token_data.get("token")
    print(f"   ✅ Token: {token[:30]}...")
    
    # 2. Call ka10080 API
    print(f"\n2️⃣ Calling ka10080 (Minute Chart)...")
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
    
    print(f"   URL: {api_url}")
    print(f"   Payload: {api_payload}")
    
    resp = requests.post(api_url, json=api_payload, headers=api_headers, verify=False)
    print(f"   Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"   ❌ Error: {resp.text[:800]}")
        return False
    
    data = resp.json()
    print(f"   ✅ Response received!")
    print(f"   Response keys: {list(data.keys())}")
    
    # 3. Check for minute chart data
    if "stk_min_pols_chart_ary" in data:
        chart_data = data["stk_min_pols_chart_ary"]
        print(f"\n3️⃣ Minute Chart Data:")
        print(f"   Total items: {len(chart_data)}")
        
        if len(chart_data) > 0:
            print(f"\n   Sample (first 3):")
            for i, item in enumerate(chart_data[:3]):
                print(f"     {i+1}. {item}")
            
            print(f"\n   Sample (last 3):")
            for i, item in enumerate(chart_data[-3:]):
                print(f"     {len(chart_data)-2+i}. {item}")
            
            # Save to CSV
            df = pd.DataFrame(chart_data)
            os.makedirs("data/proof", exist_ok=True)
            filename = f"data/proof/kiwoom_minute_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"\n   💾 Saved to: {filename}")
            
            # Analyze data
            if 'cur_prc' in chart_data[0]:
                print(f"\n   📊 Data Analysis:")
                print(f"      Columns: {list(chart_data[0].keys())}")
                if 'trde_qty' in chart_data[0]:
                    print(f"      Has volume data: YES")
                if 'cntr_tm' in chart_data[0] or 'trde_dt' in chart_data[0]:
                    print(f"      Has timestamp: YES")
            
            return True
    else:
        print(f"   ⚠️ No 'stk_min_pols_chart_ary' in response")
        print(f"   Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    return False

if __name__ == "__main__":
    result = test_kiwoom_minute_api("005930", "1")
    
    if result:
        print(f"\n{'='*80}")
        print(f"✅ Kiwoom Minute API WORKS!")
        print(f"   Next: Test historical dates")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"❌ Minute API test failed")
        print(f"{'='*80}")
