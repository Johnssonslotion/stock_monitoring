import os
import aiohttp
import asyncio

from dotenv import load_dotenv

async def verify_kis_keys():
    load_dotenv()
    kis_base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    
    if not app_key or not app_secret:
        print("❌ ERROR: KIS_APP_KEY or KIS_APP_SECRET not found in environment!")
        return False

    print(f"🔍 Testing KIS Key (First 4 chars): {app_key[:4]}...")
    
    url = f"{kis_base_url}/oauth2/tokenP"
    headers = {"content-type": "application/json; utf-8"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            status = resp.status
            data = await resp.json()
            if status == 200 and "access_token" in data:
                print(f"✅ KIS Key is NORMAL. Access Token obtained (starts with {data['access_token'][:10]}...)")
                return True
            else:
                print(f"❌ KIS Key VALIDATION FAILED. Status: {status}")
                print(f"Response: {data}")
                return False

if __name__ == "__main__":
    asyncio.run(verify_kis_keys())
