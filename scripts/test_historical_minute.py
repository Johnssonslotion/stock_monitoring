import asyncio
import os
import aiohttp
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from src.data_ingestion.price.common import KISAuthManager

load_dotenv()

async def test_historical_date(target_date="20260101", symbol="005930"):
    """
    Test if KIS API supports historical minute data retrieval
    target_date: YYYYMMDD format
    """
    print(f"🔍 Testing KIS Historical Minute Data for {target_date} ({symbol})")
    
    auth_manager = KISAuthManager()
    token = await auth_manager.get_access_token()
    
    base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("KIS_APP_KEY"),
        "appsecret": os.getenv("KIS_APP_SECRET"),
        "tr_id": "FHKST03010200",
        "custtype": "P"
    }
    
    # Try with date parameter
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_DATE_1": target_date,  # Historical date
        "FID_INPUT_HOUR_1": "153000",      # End time
        "FID_PW_DATA_INCU_YN": "Y",
        "FID_ETC_CLS_CODE": ""
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            print(f"  Status: {resp.status}")
            
            if resp.status != 200:
                text = await resp.text()
                print(f"  ❌ HTTP Error: {text}")
                return False
            
            data = await resp.json()
            rt_cd = data.get('rt_cd')
            msg = data.get('msg1')
            
            print(f"  Return Code: {rt_cd} - {msg}")
            
            if rt_cd != '0':
                print(f"  ❌ API Error: {msg}")
                print(f"  Response keys: {list(data.keys())}")
                return False
            
            items = data.get('output2', [])
            
            if isinstance(items, list) and len(items) > 0:
                print(f"  ✅ SUCCESS! Retrieved {len(items)} minute bars")
                
                # Show sample
                df = pd.DataFrame(items)
                print(f"\n  Sample data:")
                print(df[['stck_bsop_date', 'stck_cntg_hour', 'stck_prpr']].head(3).to_string(index=False))
                
                # Save proof
                os.makedirs("data/proof", exist_ok=True)
                proof_file = f"data/proof/historical_test_{target_date}_{symbol}.csv"
                df.to_csv(proof_file, index=False)
                print(f"\n  📁 Saved to: {proof_file}")
                
                return True
            else:
                print(f"  ⚠️ No data returned. Response keys: {list(data.keys())}")
                return False

if __name__ == "__main__":
    result = asyncio.run(test_historical_date("20260101", "005930"))
    if result:
        print("\n✅ Historical data retrieval is SUPPORTED!")
    else:
        print("\n❌ Historical data retrieval FAILED or NOT SUPPORTED")
