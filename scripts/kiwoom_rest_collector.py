"""
Kiwoom REST API WebSocket 실시간 데이터 수집기
PyPI kiwoom-restful 라이브러리 분석 기반 직접 구현
"""
import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp

logger = logging.getLogger(__name__)

class KiwoomRESTCollector:
    """
    Kiwoom REST API 기반 실시간 데이터 수집기
    
    핵심 차이점:
    - Direct WebSocket 연결 불가
    - REST API POST로 구독 등록 → WebSocket으로 데이터 수신
    """
    
    # API Endpoints
    BASE_URL = "https://api.kiwoom.com"
    TOKEN_URL = f"{BASE_URL}/oauth2/token"
    SUBSCRIBE_URL = f"{BASE_URL}/api/dostk/hssrt"  # 실시간 등록 (추정)
    WS_URL = "wss://api.kiwoom.com:10000"
    
    # Real Types
    REAL_TYPE_TICK = "0B"  # 주식체결
    REAL_TYPE_ORDERBOOK = "0D"  # 주식호가잔량
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.running = False
        
    async def start(self):
        """수집기 시작"""
        self.running = True
        self.session = aiohttp.ClientSession()
        
        # 1. Get Token
        await self._get_token()
        
        # 2. Connect WebSocket
        await self._connect_websocket()
        
    async def stop(self):
        """수집기 종료"""
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
            
    async def _get_token(self):
        """OAuth2 Token 발급"""
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        headers = {"Content-Type": "application/json"}
        
        async with self.session.post(self.TOKEN_URL, json=payload, headers=headers, ssl=False) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.token = data.get("access_token") or data.get("token")
                logger.info(f"✅ Token: {self.token[:10]}...")
            else:
                text = await resp.text()
                logger.error(f"Token Failed ({resp.status}): {text}")
                raise Exception(f"Token Failed: {resp.status}")
                
    async def _connect_websocket(self):
        """WebSocket 연결"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        logger.info(f"Connecting to {self.WS_URL}...")
        
        try:
            # Try with Query Parameters
            ws_url_with_params = f"{self.WS_URL}?token={self.token}"
            self.ws = await self.session.ws_connect(
                ws_url_with_params,
                headers=headers,
                ssl=False
            )
            logger.info("✅ WebSocket Connected!")
            
            # Start Message Loop
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            logger.error(f"❌ WS Connection Failed: {e}")
            raise
            
    async def _message_loop(self):
        """WebSocket 메시지 수신 루프"""
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_message(msg.data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error("❌ WS Error")
                break
                
    async def _handle_message(self, raw_data: str):
        """메시지 처리"""
        try:
            data = json.loads(raw_data)
            logger.info(f"📥 Received: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
            
            # TODO: Parse and process data
            
        except Exception as e:
            logger.debug(f"Parse Error: {e}")
            
    async def subscribe_stock(self, symbol: str, real_type: str = REAL_TYPE_TICK):
        """
        주식 실시간 데이터 구독
        
        Args:
            symbol: 종목코드 (예: '005930')
            real_type: '0B' (체결) or '0D' (호가)
        """
        # Method 1: Try WebSocket Subscribe Message
        payload = {
            "header": {
                "token": self.token,
                "tr_type": "3"  # 3: 실시간 등록
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNT0" if real_type == self.REAL_TYPE_TICK else "H0STASP0",
                    "tr_key": symbol
                }
            }
        }
        
        if self.ws and not self.ws.closed:
            await self.ws.send_json(payload)
            logger.info(f"📤 Subscribed: {symbol} ({real_type})")
        else:
            logger.warning("WebSocket not connected")


# Test Function
async def test_kiwoom_rest():
    """Kiwoom REST API 테스트"""
    from dotenv import load_dotenv
    load_dotenv(".env.backtest")
    
    app_key = os.getenv("KIWOOM_APP_KEY")
    app_secret = os.getenv("KIWOOM_APP_SECRET")
    
    collector = KiwoomRESTCollector(app_key, app_secret)
    
    try:
        await collector.start()
        
        # Subscribe to Samsung
        await collector.subscribe_stock("005930", collector.REAL_TYPE_TICK)
        
        # Wait for data
        await asyncio.sleep(10)
        
    finally:
        await collector.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_kiwoom_rest())
