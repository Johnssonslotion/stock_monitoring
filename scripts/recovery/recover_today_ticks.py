import requests
import os
import time
import json
from datetime import datetime

# Environment Variables
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
CANO = os.getenv("KIS_CANO")
ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD")

SYMBOL = "005930" # Samsung Electronics as target
TARGET_DATE = datetime.now().strftime("%Y%m%d")

def get_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    resp = requests.post(url, json={
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }, timeout=10)
    data = resp.json()
    return data.get("access_token")

def fetch_ticks_until_start(token, start_time="090000"):
    """
    Fetch ticks backwards from now until start_time using KIS inquire-time-itemconclusion
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010200", 
        "custtype": "P"
    }

    # Start from NOW (or market close if after 15:30)
    current_request_time = datetime.now().strftime("%H%M%S")
    if current_request_time > "153000":
        current_request_time = "153000"

    total_ticks = 0
    collected_data = []
    
    print(f"🚀 Starting Recovery for {SYMBOL} (Target: Today {start_time} ~ {current_request_time})")

    while True:
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": SYMBOL,
            "fid_input_hour_1": current_request_time
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code != 200:
                print(f"❌ Error {resp.status_code}: {resp.text}")
                break
                
            data = resp.json()
            if data['rt_cd'] != '0':
                print(f"❌ API Error: {data['msg1']}")
                break
                
            ticks = data.get('output1', [])
            if not ticks:
                print("⚠️ No more data returned.")
                break
                
            # Filter and Collect
            # input_hour_1 is EXCLUSIVE or INCLUSIVE depending on implementation?
            # KIS usually returns latest ticks BEFORE request_time.
            
            for t in ticks:
                t_time = t['stck_cntg_hour']
                # Check limits
                if t_time < start_time:
                    print(f"✅ Reached start time limit: {t_time}")
                    return collected_data
                
                collected_data.append(t)
            
            last_time = ticks[-1]['stck_cntg_hour']
            count = len(ticks)
            total_ticks += count
            
            print(f"📥 Fetched {count} ticks. Last Time: {last_time} (Total: {total_ticks})")
            
            # Next request time = Last tick time
            # Important: To avoid overlap or stuck loop, ensure we move backward.
            # KIS Logic: asking for HHMMSS returns ticks <= HHMMSS.
            # If we pass last_time, we might get duplicates if many ticks in same second.
            # But let's verify simply by time update.
            
            if last_time >= current_request_time and count > 0:
                 # Stuck check (should rely on API cursor if available, but KIS uses time)
                 # If stuck, maybe manipulate time slightly? KIS doesn't have next_key for this TR.
                 print("⚠️ Time did not move backward. Breaking loop to protect TPS.")
                 break
                 
            current_request_time = last_time
            
            # Rate Limit Protection
            time.sleep(0.2) 
            
            # Limit for test run (don't run forever here)
            if total_ticks > 500: 
                print("🛑 Test Limit Reached (500 ticks). Stopping for verification.")
                break
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            break
            
    return collected_data

if __name__ == "__main__":
    token = get_token()
    if token:
        ticks = fetch_ticks_until_start(token, "090000")
        print(f"🏁 Recovery Complete. Captured {len(ticks)} ticks.")
        if ticks:
            print(f"   First (Newest): {ticks[0]['stck_cntg_hour']} {ticks[0]['stck_prpr']}")
            print(f"   Last  (Oldest): {ticks[-1]['stck_cntg_hour']} {ticks[-1]['stck_prpr']}")
    else:
        print("❌ Token Generation Failed")
