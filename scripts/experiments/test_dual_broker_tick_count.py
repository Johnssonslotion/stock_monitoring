"""
Dual Broker Tick Count Verification Test - WITH AUTO-TOKEN

Tests both KIS and Kiwoom APIs with automatic token generation.
Safe to run alongside containers (each uses independent tokens).
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load .env.backtest (not default .env)
load_dotenv(".env.backtest")

# API Configuration
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")

KIWOOM_BASE_URL = "https://api.kiwoom.com"
KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")


async def get_kis_token():
    """Get KIS Access Token (auto-generated)"""
    url = f"{KIS_BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json; utf-8"}
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("access_token")
            else:
                error = await resp.text()
                print(f"❌ KIS Token Error: {error[:200]}")
                return None


async def get_kiwoom_token():
    """Get Kiwoom OAuth2 Token (auto-generated)"""
    url = f"{KIWOOM_BASE_URL}/oauth2/token"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    body = {
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("token")
            else:
                error = await resp.text()
                print(f"❌ Kiwoom Token Error: {error[:200]}")
                return None


async def test_kis_tick_count(symbol="005930"):
    """Test KIS Tick API (FHKST01010300)"""
    print("\n" + "="*60)
    print("🔵 Testing KIS Tick API (FHKST01010300)")
    print("="*60)
    
    token = await get_kis_token()
    if not token:
        return {'success': False, 'api': 'KIS', 'reason': 'token_failed'}
    
    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    current_time = datetime.now().strftime("%H%M%S")
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010300",
        "custtype": "P"
    }
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_HOUR_1": current_time
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, params=params) as resp:
                print(f"Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get('output1', [])
                    print(f"✅ SUCCESS: {len(items)} ticks returned")
                    
                    if items:
                        print(f"Sample: {items[0].get('stck_cntg_hour', 'N/A')} - {items[0].get('stck_prpr', 'N/A')}원")
                        return {'success': True, 'count': len(items), 'api': 'KIS'}
                    else:
                        print("⚠️ No ticks at this time")
                        return {'success': True, 'count': 0, 'api': 'KIS'}
                else:
                    error = await resp.text()
                    print(f"❌ Error: {error[:200]}")
                    return {'success': False, 'api': 'KIS'}
        except Exception as e:
            print(f"❌ Exception: {e}")
            return {'success': False, 'api': 'KIS'}


async def test_kiwoom_tick_count(symbol="005930"):
    """Test Kiwoom Tick API (ka10079)"""
    print("\n" + "="*60)
    print("🟢 Testing Kiwoom Tick API (ka10079)")
    print("="*60)
    
    token = await get_kiwoom_token()
    if not token:
        return {'success': False, 'api': 'Kiwoom', 'reason': 'token_failed'}
    
    url = f"{KIWOOM_BASE_URL}/api/dostk/chart"
    
    headers = {
        "authorization": f"Bearer {token}",
        "api-id": "ka10079",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "cont-yn": "N"
    }
    
    body = {
        "stk_cd": symbol,
        "tic_scope": "1",
        "upd_stkpc_tp": "0"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=body) as resp:
                print(f"Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    ticks = data.get("stk_tic_chart_qry", [])
                    print(f"✅ SUCCESS: {len(ticks)} ticks returned")
                    
                    if ticks:
                        print(f"Time range: {ticks[0].get('cntr_tm')} ~ {ticks[-1].get('cntr_tm')}")
                        print(f"Sample: {ticks[0].get('cntr_tm')} - {ticks[0].get('cur_prc')}원")
                        return {'success': True, 'count': len(ticks), 'api': 'Kiwoom'}
                    else:
                        print("⚠️ No ticks (today only API, may not have past data)")
                        return {'success': True, 'count': 0, 'api': 'Kiwoom'}
                elif resp.status == 429:
                    print("❌ Rate Limited")
                    return {'success': False, 'api': 'Kiwoom', 'error': 'rate_limit'}
                else:
                    error = await resp.text()
                    print(f"❌ Error: {error[:200]}")
                    return {'success': False, 'api': 'Kiwoom'}
        except Exception as e:
            print(f"❌ Exception: {e}")
            return {'success': False, 'api': 'Kiwoom'}


async def main():
    print("\n🧪 Dual Broker Tick Count API Test")
    print(f"Symbol: 005930 (삼성전자)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"✅ Auto-Token Generation (Safe for containers)")
    
    # Test both APIs
    kis_result = await test_kis_tick_count()
    kiwoom_result = await test_kiwoom_tick_count()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    print(f"\n🔵 KIS API:")
    if kis_result.get('success'):
        print(f"  ✅ Working - {kis_result.get('count', 0)} ticks")
    else:
        print(f"  ❌ Failed - {kis_result.get('reason', 'unknown')}")
    
    print(f"\n🟢 Kiwoom API:")
    if kiwoom_result.get('success'):
        print(f"  ✅ Working - {kiwoom_result.get('count', 0)} ticks")
    else:
        print(f"  ❌ Failed - {kiwoom_result.get('reason', 'unknown')}")
    
    # Recommendation
    print("\n💡 RECOMMENDATION:")
    if kis_result.get('success') and kis_result.get('count', 0) > 0:
        print("  ✅ Use KIS API (FHKST01010300) for tick count verification")
        print("  → Supports time-based queries (FID_INPUT_HOUR_1)")
    elif kiwoom_result.get('success') and kiwoom_result.get('count', 0) > 0:
        print("  ✅ Use Kiwoom API (ka10079) for tick count verification")
        print("  ⚠️ TODAY ONLY - no date parameter")
    else:
        print("  ⚠️ Both returned 0 or failed. Check:")
        print("    1. Market is open")
        print("    2. Credentials are valid")
        print("    3. Run during past market hours (e.g. 10:00-11:00)")


if __name__ == "__main__":
    asyncio.run(main())
