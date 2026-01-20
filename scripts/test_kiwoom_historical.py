import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

load_dotenv()

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_kiwoom_token():
    """Get Kiwoom OAuth2 token"""
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    token_url = "https://api.kiwoom.com/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    
    resp = requests.post(token_url, json=payload, headers=headers, verify=False)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("return_code") == 0:
            return data.get("token")
    return None

def fetch_kiwoom_minute(token, symbol, target_date=None):
    """
    Fetch minute data from Kiwoom ka10080
    target_date: YYYYMMDD format (optional - if no date, returns today)
    """
    api_url = "https://api.kiwoom.com/api/dostk/chart"
    headers = {
        "api-id": "ka10080",
        "authorization": f"Bearer {token}",
        "content-yn": "N",
        "Content-Type": "application/json;charset=UTF-8"
    }
    
    payload = {
        "stk_cd": symbol,
        "tic_scope": "1",  # 1 minute
        "upd_stakc_lp": "1",
        "upd_stkpc_tp": "0"
    }
    
    # Try adding date if provided
    if target_date:
        # Not sure if ka10080 supports historical dates
        # Will test with different parameter names
        payload["date"] = target_date  # Try this
    
    resp = requests.post(api_url, json=payload, headers=headers, verify=False)
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get("return_code") == 0:
            # Correct key: stk_min_pole_chart_qry
            return data.get("stk_min_pole_chart_qry", [])
    
    return []

def test_historical_date():
    """Test if Kiwoom API supports historical dates"""
    print("🧪 Testing Kiwoom Historical Date Support")
    print("="*80)
    
    token = get_kiwoom_token()
    if not token:
        print("❌ Failed to get token")
        return
    
    print(f"✅ Token obtained")
    
    # Test 1: Today (baseline)
    print(f"\n1️⃣ Test: Today (2026-01-19)")
    today_data = fetch_kiwoom_minute(token, "005930")
    print(f"   Result: {len(today_data)} items")
    if today_data:
        print(f"   Sample: {today_data[0]}")
    
    # Test 2: Historical date (2026-01-01)
    print(f"\n2️⃣ Test: Historical (2026-01-01)")
    hist_data = fetch_kiwoom_minute(token, "005930", "20260101")
    print(f"   Result: {len(hist_data)} items")
    if hist_data:
        print(f"   Sample: {hist_data[0]}")
        print(f"   ✅ Historical data WORKS!")
        return True
    else:
        print(f"   ❌ Historical data NOT SUPPORTED or different parameter needed")
        return False

if __name__ == "__main__":
    result = test_historical_date()
    
    if result:
        print(f"\n{'='*80}")
        print(f"✅ Kiwoom SUPPORTS historical minute data!")
        print(f"   Ready to backfill 1/1-1/18")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"⚠️ Historical date support unclear")
        print(f"   May need different API or parameter")
        print(f"{'='*80}")
