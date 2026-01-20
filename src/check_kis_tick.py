import asyncio
import aiohttp
import os
import json
import sys

from dotenv import load_dotenv

# Flush stdout immediately
sys.stdout.reconfigure(line_buffering=True)
load_dotenv()

from src.data_ingestion.price.common import KISAuthManager

BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")

async def fetch_tick_data():
    auth_manager = KISAuthManager()
    try:
        token = await auth_manager.get_access_token()
    except Exception as e:
        print(f"❌ Auth Error: {e}")
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
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=10) as res:
                print(f"Status: {res.status}", flush=True)
                if res.status == 200:
                    data = await res.json()
                    rt_cd = data.get('rt_cd')
                    msg1 = data.get('msg1')
                    output2 = data.get('output2', [])
                    
                    print(f"Return Code: {rt_cd} ({msg1})", flush=True)
                    
                    # FHKST01010400 sometimes returns a dict in output2 for summary
                    # and output1 for list, OR vice versa. 
                    # Let's check both output1 and output2 for a list.
                    tick_list = []
                    for out_key in ['output1', 'output2']:
                        val = data.get(out_key)
                        if isinstance(val, list) and len(val) > 0:
                            tick_list = val
                            print(f"✅ Found list in {out_key}")
                            break
                    
                    print(f"Total Count: {len(tick_list)}", flush=True)
                    
                    if tick_list:
                        print("First 3 records:", flush=True)
                        for item in tick_list[:3]:
                            print(f" - Time: {item.get('stck_cntg_hour')}, Price: {item.get('stck_prpr')}, Vol: {item.get('cntg_vol')}", flush=True)
                        print("\n✅ Verification SUCCESS: Tick data retrieval is possible via REST API.", flush=True)
                    else:
                        print("⚠️ No list data found in output1 or output2.", flush=True)
                        print(f"Response keys: {list(data.keys())}")
                else:
                    text = await res.text()
                    print(f"❌ HTTP Error: {text}", flush=True)
            
    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(fetch_tick_data())
