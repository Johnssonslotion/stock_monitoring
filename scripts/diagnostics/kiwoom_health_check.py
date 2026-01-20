
import requests
import json
import sys

def check_kiwoom():
    url = "https://api.kiwoom.com/oauth2/token"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {"grant_type": "client_credentials"} # 더미 페이로드
    
    print(f"--- Kiwoom Connection Test ---")
    print(f"Destination: {url}")
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {resp.status_code}")
        print(f"Headers: {dict(resp.headers)}")
        print(f"Body: {resp.text[:500]}")
        
        if resp.status_code == 400 and "Request Blocked" in resp.text:
            print("\n🚨 [ALERT] IP 또는 헤더 기반 차단 감지 (Akamai Blocked)")
        elif resp.status_code == 403:
            print("\n🚨 [ALERT] 403 Forbidden - IP 차단 가능성 높음")
        elif resp.status_code == 200 or ("invalid_client" in resp.text):
            print("\n✅ 서버 접속 성공 (내용은 인증 실패일 수 있으나 네트워크는 개방됨)")
            
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")

if __name__ == "__main__":
    check_kiwoom()
