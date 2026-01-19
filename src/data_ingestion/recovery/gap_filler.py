import requests
import os
import time
import csv
from datetime import datetime
import sys
import pytz

import os

# Constants
BASE_URL = "https://openapi.koreainvestment.com:9443"
# Debugging Environment
print(f"🔍 Environment Keys: {[k for k in os.environ.keys() if 'KIS' in k]}")
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
SYMBOL = "005930"  # Target: Samsung Electronics
OUTPUT_DIR = "/app/data/recovery"
OUTPUT_FILE = f"{OUTPUT_DIR}/tick_recovery_{datetime.now().strftime('%Y%m%d')}_{SYMBOL}.csv"

def get_token():
    url = f"{BASE_URL}/oauth2/tokenP"
    try:
        resp = requests.post(url, json={
            "grant_type": "client_credentials",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET
        }, timeout=10)
        data = resp.json()
        if "access_token" in data:
            return data["access_token"]
        else:
            print(f"❌ Token Resp Error: {data}")
            return None
    except Exception as e:
        print(f"❌ Token Check Failed: {e}")
        return None

def fetch_all_ticks_today():
    token = get_token()
    if not token:
        print("❌ Cannot get token.")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"🚀 Starting Full Recovery for {SYMBOL} (Target: 09:00:00 ~ Now)")
    
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010200", 
        "custtype": "P"
    }

    target_time = "090500" # Target: 5 minutes after open to get opening data
    print(f"Start Time (Target): {target_time}")
    
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "price", "volume", "type"])

        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": SYMBOL,
            "fid_input_hour_1": target_time
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            data = resp.json()
            ticks = data.get('output1', [])
            
            for t in ticks:
                writer.writerow([t['stck_cntg_hour'], t['stck_prpr'], t['cntg_vol'], "1"])
            
            print(f"🏁 Recovery Done. Saved {len(ticks)} opening ticks to {OUTPUT_FILE}")
            if ticks:
                print(f"Sample: {ticks[-1]['stck_cntg_hour']} ~ {ticks[0]['stck_cntg_hour']}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    fetch_all_ticks_today()
