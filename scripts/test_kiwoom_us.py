import asyncio
import os
import json
import logging
import sys
from dotenv import load_dotenv
import aiohttp

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("KiwoomUSTest")

# .env.backtest 로드
load_dotenv(".env.backtest")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
KIWOOM_MOCK = os.getenv("KIWOOM_MOCK", "False").lower() == "true"

# Domain Selection
BASE_DOMAIN = "mockapi.kiwoom.com" if KIWOOM_MOCK else "api.kiwoom.com"
REST_URL = f"https://{BASE_DOMAIN}/oauth2/token"
WS_URL = f"wss://{BASE_DOMAIN}:10000/api/dostk/websocket"

async def get_access_token(session):
    """Get OAuth2 Access Token"""
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET
    }
    
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }
    
    logger.info(f"🔑 Requesting Token from {REST_URL}...")
    try:
        async with session.post(REST_URL, headers=headers, json=payload, ssl=False) as resp:
            text = await resp.text()
            if resp.status == 200:
                data = json.loads(text)
                token = data.get("access_token") or data.get("token")
                if token:
                    logger.info(f"✅ Token Received: {token[:10]}...")
                else:
                    logger.error("❌ Token field missing!")
                return token
            else:
                logger.error(f"❌ Token Failed ({resp.status}): {text}")
                return None
    except Exception as e:
        logger.error(f"❌ Token Request Error: {e}")
        return None

async def test_kr_stock(ws, token):
    """한국 주식 테스트 (삼성전자)"""
    logger.info("=" * 60)
    logger.info("🇰🇷 Testing KOREAN Stock (Samsung Electronics 005930)")
    logger.info("=" * 60)
    
    payload = {
        "header": {
            "token": token,
            "tr_type": "3",
            "content-type": "utf-8"
        },
        "body": {
            "input": {
                "tr_id": "H0STCNT0",  # 국내 주식 체결
                "tr_key": "005930"
            }
        }
    }
    
    await ws.send_json(payload)
    logger.info("📤 Sent KR subscription")
    
    # Wait for response
    for _ in range(5):
        try:
            msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                logger.info(f"📥 KR Response: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                return True
        except asyncio.TimeoutError:
            continue
    
    logger.warning("⚠️ No KR response received")
    return False

async def test_us_stock(ws, token):
    """미국 주식 테스트 (애플)"""
    logger.info("=" * 60)
    logger.info("🇺🇸 Testing US Stock (Apple AAPL)")
    logger.info("=" * 60)
    
    # 여러 가능한 TR_ID 시도
    possible_tr_ids = [
        "HDFSCNI0",  # 해외주식 실시간체결 (추정)
        "HDFSCNT0",  # 해외주식 체결 (추정)
        "HDFSSCNI",  # 변형
        "H0USSTK0",  # US Stock (추정)
    ]
    
    for tr_id in possible_tr_ids:
        logger.info(f"🔍 Trying TR_ID: {tr_id}")
        
        payload = {
            "header": {
                "token": token,
                "tr_type": "3",
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": tr_id,
                    "tr_key": "AAPL"  # 애플 티커
                }
            }
        }
        
        await ws.send_json(payload)
        logger.info(f"📤 Sent US subscription (TR_ID: {tr_id})")
        
        # Wait for response
        for _ in range(3):
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    logger.info(f"📥 US Response ({tr_id}): {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
                    
                    # Check for error
                    if "return_code" in data:
                        code = data.get("return_code")
                        msg_text = data.get("return_msg", "")
                        if str(code) == "0":
                            logger.info(f"✅ SUCCESS with TR_ID: {tr_id}")
                            return True
                        else:
                            logger.warning(f"❌ Error Code {code}: {msg_text}")
                    
            except asyncio.TimeoutError:
                continue
        
        logger.warning(f"⚠️ No response for {tr_id}, trying next...")
        await asyncio.sleep(1)
    
    logger.error("❌ All TR_IDs failed for US stock")
    return False

async def test_connection():
    if not KIWOOM_APP_KEY or not KIWOOM_APP_SECRET:
        logger.error("❌ .env.backtest에 KIWOOM_APP_KEY/SECRET이 없습니다.")
        return

    logger.info(f"🚀 Target Env: {'MOCK' if KIWOOM_MOCK else 'REAL'}")
    logger.info(f"🎯 Testing US Stock Data Collection Capability")
    
    async with aiohttp.ClientSession() as session:
        # 1. Get Token
        token = await get_access_token(session)
        if not token:
            return
        
        # 2. Connect WS
        logger.info(f"🚀 Connecting to {WS_URL}...")
        try:
            async with session.ws_connect(WS_URL, ssl=False) as ws:
                logger.info("✅ WebSocket Connected!")
                
                # 3. Test Korean Stock (Baseline)
                kr_success = await test_kr_stock(ws, token)
                
                await asyncio.sleep(2)
                
                # 4. Test US Stock
                us_success = await test_us_stock(ws, token)
                
                # 5. Summary
                logger.info("=" * 60)
                logger.info("📊 TEST SUMMARY")
                logger.info("=" * 60)
                logger.info(f"🇰🇷 Korean Stock (005930): {'✅ SUCCESS' if kr_success else '❌ FAILED'}")
                logger.info(f"🇺🇸 US Stock (AAPL): {'✅ SUCCESS' if us_success else '❌ FAILED'}")
                
                if us_success:
                    logger.info("🎉 Kiwoom supports US real-time data!")
                    logger.info("💡 You can use Kiwoom as backup for US market")
                else:
                    logger.warning("⚠️ US real-time may require:")
                    logger.warning("   1. Paid subscription ($8/month)")
                    logger.warning("   2. Previous month trading activity")
                    logger.warning("   3. Different TR_ID (check Kiwoom docs)")
                
        except Exception as e:
            logger.error(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
