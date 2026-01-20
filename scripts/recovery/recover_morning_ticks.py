import asyncio
import aiohttp
import os
import json
import sys
import yaml
from datetime import datetime, timedelta
from typing import List, Dict

from dotenv import load_dotenv

# Ensure src path is available
sys.path.append(os.getcwd())
load_dotenv()

from src.data_ingestion.price.common import KISAuthManager

BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
RECOVERY_DIR = "data/raw/recovery"

def load_symbols() -> List[str]:
    with open("configs/kr_symbols.yaml", "r") as f:
        config = yaml.safe_load(f)
    # Extract symbols with "Core 40" tag or just all symbols?
    # Council said "Core 40". Let's try to filter or take top 40.
    # The config structure is likely a list of objects.
    # Assuming simple list or dict.
    symbols_list = []
    
    # 1. Indices
    if 'indices' in config.get('symbols', {}):
        for item in config['symbols']['indices']:
            if 'symbol' in item: symbols_list.append(item['symbol'])

    # 2. Leverage
    if 'leverage' in config.get('symbols', {}):
        for item in config['symbols']['leverage']:
            if 'symbol' in item: symbols_list.append(item['symbol'])
            
    # 3. Sectors
    if 'sectors' in config.get('symbols', {}):
        for sector_name, sector_data in config['symbols']['sectors'].items():
            # ETF
            if 'etf' in sector_data and 'symbol' in sector_data['etf']:
                symbols_list.append(sector_data['etf']['symbol'])
            
            # Top3
            if 'top3' in sector_data:
                for item in sector_data['top3']:
                    if 'symbol' in item: symbols_list.append(item['symbol'])
                    
    # Remove duplicates
    return list(set(symbols_list))

async def fetch_ticks(session, token: str, symbol: str, time_str: str) -> List[Dict]:
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010300",
        "custtype": "P"
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": symbol,
        "fid_input_hour_1": time_str
    }
    
    async with session.get(url, headers=headers, params=params) as res:
        if res.status != 200:
            print(f"❌ [{symbol}] Error {res.status}: {await res.text()}")
            return []
        data = await res.json()
        if data.get('rt_cd') != '0':
            print(f"⚠️ [{symbol}] API Fail {data.get('rt_cd')}: {data.get('msg1')}")
        return data.get('output2', []) or data.get('output1', [])

async def recover_symbol(auth_manager, symbol: str):
    try:
        token = await auth_manager.get_access_token()
        async with aiohttp.ClientSession() as session:
            # Time range: 083000 to "now" (e.g. 091000)
            # Iterate every minute? The API returns the "latest" relative to the time?
            # Actually inquire-time-itemconclusion searches *backwards* from the given time?
            # Or it returns a list around that time.
            # Strategy: Query every 10 minutes to cover the gap.
            # Gap: 08:30 to 09:20 -> 50 mins.
            # Points: 084000, 085000, 090000, 091000, 092000?
            # This API returns ~30 ticks. 1 min loop is safer.
            
            os.makedirs(RECOVERY_DIR, exist_ok=True)
            filename = f"{RECOVERY_DIR}/recovery_{symbol}_20260120.jsonl"
            
            with open(filename, "a", encoding="utf-8") as f:
                # KST Timezone logic
                kst_offset = timedelta(hours=9)
                now_kst = datetime.utcnow() + kst_offset
                
                # Start 08:30 KST
                start_time = now_kst.replace(hour=8, minute=30, second=0, microsecond=0)
                # If now is before 08:30 (rare case in test), clamping? 
                # Assuming script runs AFTER 08:30.
                
                # End: 09:13 KST (User Request)
                # Fixed end time
                end_time = now_kst.replace(hour=9, minute=13, second=0, microsecond=0)
                
                current_time = start_time
                print(f"[{symbol}] Recovery range (KST): {start_time.strftime('%H:%M:%S')} ~ {end_time.strftime('%H:%M:%S')}")
                
                while current_time < end_time:
                    time_str = current_time.strftime("%H%M%S")
                    ticks = await fetch_ticks(session, token, symbol, time_str)
                    
                    if ticks:
                        for t in ticks:
                            # Add metadata
                            t['symbol'] = symbol
                            t['fetched_at_time_cond'] = time_str
                            f.write(json.dumps(t, ensure_ascii=False) + "\n")
                        f.flush() # Ensure write
                        print(f"[{symbol}] Wrote {len(ticks)} ticks for {time_str}")
                    else:
                        # print(f"[{symbol}] No ticks for {time_str}")
                        pass
                    
                    current_time += timedelta(minutes=1) # 1 min step for better coverage
                    await asyncio.sleep(1.2) # Rate limit protection (1.2s > 1s/req)
                    
            print(f"✅ Recovered {symbol}")
            
    except Exception as e:
        print(f"❌ Failed {symbol}: {e}")

async def main():
    print("🚀 Starting Emergency Tick Recovery (08:30+)")
    symbols = load_symbols()
    print(f"Found {len(symbols)} symbols. Recovering...")
    
    auth = KISAuthManager()
    
    # Process in chunks of 5 parallel
    chunk_size = 5
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i+chunk_size]
        await asyncio.gather(*(recover_symbol(auth, s) for s in chunk))
        
    print("🎉 Recovery Complete.")

if __name__ == "__main__":
    asyncio.run(main())
