import requests
import json
import os
import sys
from datetime import datetime
import time

# Load Credentials (Simple loader for script)
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
CANO = os.getenv("KIS_CANO")        # Account No (if needed, usually not for market data but good to have)
ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD")

BASE_URL = "https://openapi.koreainvestment.com:9443"

def get_access_token():
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    
    print(f"🔑 Getting Access Token...")
    try:
        res = requests.post(url, json=body, headers=headers, timeout=10)
        data = res.json()
        if "access_token" in data:
            print("✅ Token Received")
            return data["access_token"]
        else:
            print(f"❌ Token Failed: {data}")
            return None
    except Exception as e:
        print(f"❌ Token Request Error: {e}")
        return None

def fetch_minute_chart(token, symbol="005930", time_code="123000"):
    """
    Fetch minute chart data
    URL: /uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice
    TR_ID: FHKST03010200
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST03010200", # 주식 현재가 시세 (분봉 조회용 TR)
        "custtype": "P"
    }
    
    # KIS REST API expects specific query params
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": symbol,
        "fid_input_hour_1": time_code, 
        "fid_pw_data_incu_yn": "N"  # Password data inclusion
    }
    
    print(f"📊 Fetching Minute Data for {symbol} at {time_code}...")
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            rt_cd = data.get('rt_cd')
            if rt_cd == '0':
                output2 = data.get('output2', []) # History data usually in output2
                print(f"✅ Data Fetch Success! Received {len(output2)} records")
                if output2:
                    print(f"   First Record: {output2[0]}")
                return True
            else:
                print(f"❌ API Error: {data.get('msg1')}")
                print(f"   Full Response: {data}")
        else:
            print(f"❌ HTTP Error {res.status_code}: {res.text}")
            
    except Exception as e:
        print(f"❌ Request Exception: {e}")
        
    return False

if __name__ == "__main__":
    if not APP_KEY or not APP_SECRET:
        print("❌ Credentials not found in environment")
        sys.exit(1)
        
    token = get_access_token()
    if token:
        # Check retrieval
        # Using 005930 (Samsung Elecs)
        # Using a fixed time or current time doesn't strictly matter for test, 
        # but let's try to get recent data.
        now_hm = datetime.now().strftime("%H%M%S")
        fetch_minute_chart(token, "005930", now_hm)
