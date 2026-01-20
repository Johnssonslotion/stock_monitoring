
import asyncio
import os
import json
import logging
import aiohttp
# from dotenv import load_dotenv

import os

KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API_Verifier")

# load_dotenv()

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
# Assuming Real Environment for verification as Mock might not support all TRs
KIWOOM_REST_URL = "https://api.kiwoom.com" 

async def get_kiwoom_token():
    url = f"{KIWOOM_REST_URL}/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET
    }
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            text = await resp.text()
            if resp.status == 200:
                return json.loads(text).get("token")
            else:
                logger.error(f"Token Fail ({resp.status}): {text}")
                return None

async def verify_kiwoom_opt10079(token):
    """주식틱차트조회 (opt10079) 검증"""
    endpoints = [
        "/api/v1/daily/chart", # Spec v1
        "/api/tr/opt10079",
        "/openapi/tr/opt10079",
        "/v1/api/tr/opt10079"
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "tr_id": "opt10079", # Some APIs use this
        "api-id": "opt10079"
    }
    
    body = {
        "stk_cd": "005930", # Try both naming conventions
        "종목코드": "005930",
        "tic_scope": "1",
        "틱범위": "1",
        "upd_objec_tp": "1",
        "수정주가구분": "1"
    }
    
    async with aiohttp.ClientSession() as session:
        for path in endpoints:
            url = f"{KIWOOM_REST_URL}{path}"
            logger.info(f"Targeting: {url}")
            try:
                async with session.post(url, headers=headers, json=body) as resp:
                    text = await resp.text()
                    logger.info(f"Response ({resp.status}): {text[:200]}")
            except Exception as e:
                logger.error(f"Err: {e}")

async def get_kis_token():
    url = f"{KIS_BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data.get("access_token")
            else:
                logger.error(f"KIS Token Fail: {data}")
                return None

async def verify_kis_chart(token):
    # 국내주식 분봉조회 (주식당일분봉)
    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST03010200", # 주식당일분봉조회
        "custtype": "P"
    }
    
    params = {
        "FID_ETC_CLS_CODE": "",
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": "005930",
        "FID_INPUT_HOUR_1": "153000", # 15:30 기준 역순 조회
        "FID_PW_DATA_INCU_YN": "Y"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            logger.info(f"KIS Status: {resp.status}")
            output2 = data.get("output2", [])
            if output2:
                first_row = output2[0]
                logger.info(f"KIS Data Sample: {first_row}")
                # Check for tick count or volume
                logger.info(f"Checking fields: {list(first_row.keys())}")
            else:
                logger.warning(f"No KIS Data: {data}")

async def verify_kis_ticks(token):
    # 주식현재가 체결 (Tick History)
    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010300", # 주식현재가 시세(체결)
        "custtype": "P"
    }
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": "005930",
        "FID_INPUT_HOUR_1": "100000" # 10:00:00 이전(?) or 기준 체결 조회 - Testing History Depth
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            logger.info(f"KIS Ticks Status: {resp.status}")
            output1 = data.get("output1", [])
            if output1:
                first_row = output1[0]
                logger.info(f"KIS Tick Sample: {first_row}")
                # Fields check: stck_prpr (Price), cntg_vol (Volume/TickSize), acml_vol (Accumulated)
            else:
                logger.warning(f"No KIS Tick Data: {data}")

async def main():
    if KIWOOM_APP_KEY:
        pass
    
    if KIS_APP_KEY:
        logger.info("2. [KIS] Getting Token...")
        token = await get_kis_token()
        if token:
            logger.info("3. [KIS] Verifying Ticks (FHKST01010300)...")
            await verify_kis_ticks(token)


if __name__ == "__main__":
    asyncio.run(main())
