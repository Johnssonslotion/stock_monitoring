import requests
import os
import json

KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

def get_token():
    url = f"{KIS_BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    res = requests.post(url, json=body)
    return res.json().get("access_token")

def test_1m(token, symbol):
    # Try different TR IDs
    # FHKST03010200 is "주식 당일 시간별 체결가"
    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST03010200",
        "custtype": "P"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_HOUR_1": "",
        "FID_PW_RESV_RE3": "",
        "FID_ETC_CLS_CODE": ""
    }
    res = requests.get(url, headers=headers, params=params)
    print(f"Symbol: {symbol}, TR: {headers['tr_id']}")
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    token = get_token()
    if token:
        test_1m(token, "005930")
    else:
        print("Failed to get token")
