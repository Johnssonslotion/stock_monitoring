import requests
import os
import json
import sys

# Flush stdout immediately
sys.stdout.reconfigure(line_buffering=True)

def get_access_token(base_url, app_key, app_secret):
    url = f"{base_url}/oauth2/tokenP"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    
    print(f"🔑 Requesting Token from {url}...", flush=True)
    try:
        res = requests.post(url, json=body, headers=headers, timeout=10)
        data = res.json()
        token = data.get("access_token")
        if token:
            print("✅ Token Received", flush=True)
            return token
        else:
            print(f"❌ Token Failed: {data}", flush=True)
            return None
    except Exception as e:
        print(f"❌ Token Error: {e}", flush=True)
        return None

def fetch_tick_data():
    APP_KEY = os.getenv("KIS_APP_KEY")
    APP_SECRET = os.getenv("KIS_APP_SECRET")
    BASE_URL = "https://openapi.koreainvestment.com:9443"
    
    if not APP_KEY:
        print("❌ ENV KIS_APP_KEY not found", flush=True)
        return

    token = get_access_token(BASE_URL, APP_KEY, APP_SECRET)
    if not token:
        return

    # KIS TR: FHKST01010400 (주식시세-주식현재가 체결가)
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010400",
        "custtype": "P"
    }
    
    # Check for 005930 (Samsung Electronics) around 13:00:00
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": "005930",
        "fid_input_hour_1": "130000" 
    }
    
    print(f"📊 Testing KIS Tick Response for 005930 at {params['fid_input_hour_1']}...", flush=True)
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"Status: {res.status_code}", flush=True)
        if res.status_code == 200:
            data = res.json()
            rt_cd = data.get('rt_cd')
            msg1 = data.get('msg1')
            output2 = data.get('output2', [])
            
            print(f"Return Code: {rt_cd} ({msg1})", flush=True)
            print(f"Total Count: {len(output2)}", flush=True)
            
            if output2:
                print("First 3 records:", flush=True)
                for item in output2[:3]:
                    # stck_cntg_hour: Time, stck_prpr: Price, cntg_vol: Volume
                    print(f" - Time: {item.get('stck_cntg_hour')}, Price: {item.get('stck_prpr')}, Vol: {item.get('cntg_vol')}", flush=True)
                
                print("\n✅ Verification SUCCESS: Tick data retrieval is possible via REST API.", flush=True)
            else:
                print("⚠️ No data in output2. (Market closed or time mismatch?)", flush=True)
        else:
            print(f"❌ HTTP Error: {res.text}", flush=True)
            
    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

if __name__ == "__main__":
    fetch_tick_data()
