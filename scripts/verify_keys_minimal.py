import requests
import os
from dotenv import load_dotenv

load_dotenv()

def verify_kis():
    print("--- KIS Key Verification ---")
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    
    # 1. Access Token
    url = f"{base_url}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if "access_token" in data:
            print("✅ KIS Access Token: SUCCESS")
        else:
            print(f"❌ KIS Access Token: FAILED - {data}")
            return
    except Exception as e:
        print(f"❌ KIS Access Token: ERROR - {e}")
        return

    # 2. Approval Key (for WebSocket)
    url = f"{base_url}/oauth2/Approval"
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if "approval_key" in data:
            print(f"✅ KIS Approval Key: SUCCESS")
        else:
            print(f"❌ KIS Approval Key: FAILED - {data}")
    except Exception as e:
        print(f"❌ KIS Approval Key: ERROR - {e}")

def verify_kiwoom():
    print("\n--- Kiwoom Key Verification ---")
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    url = "https://api.kiwoom.com/oauth2/token"
    
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "token" in data:
                print("✅ Kiwoom Token: SUCCESS")
            else:
                print(f"✅ Kiwoom Token: SUCCESS (Response OK, but token field missing or named differently: {data.keys()})")
        else:
            print(f"❌ Kiwoom Token: FAILED - HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Kiwoom Token: ERROR - {e}")

if __name__ == "__main__":
    verify_kis()
    verify_kiwoom()
