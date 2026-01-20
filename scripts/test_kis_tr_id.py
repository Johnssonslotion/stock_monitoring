import asyncio
import aiohttp
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from src.data_ingestion.price.common import KISAuthManager

BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")

async def test_tr(tr_id, symbol="005930", time_str="090100"):
    print(f"\n--- Testing TR ID: {tr_id} ---")
    auth_manager = KISAuthManager()
    token = await auth_manager.get_access_token()
    
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
        "custtype": "P"
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": symbol,
        "fid_input_hour_1": time_str
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as res:
            print(f"Status: {res.status}")
            text = await res.text()
            if res.status == 200:
                data = await res.json()
                items = data.get('output1', [])
                print(f"Output1 Count: {len(items)}")
                if items:
                    print(f"First Item: {items[0]}")
            else:
                print(f"Error: {text}")

async def main():
    print(f"Testing for Symbol 005930 at 090100...")
    await test_tr("FHKST01010300")
    await test_tr("FHKST01010400")

if __name__ == "__main__":
    asyncio.run(main())
