"""
KIS API 인증 관리 모듈 (KR/US 공용)
"""
import os
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")


class KISAuthManager:
    """KIS API 인증 관리자 (KR/US 공용)"""
    
    def __init__(self):
        self.approval_key: Optional[str] = None
    
    async def get_approval_key(self) -> str:
        """
        KIS 웹소켓 접속을 위한 전용 Approval Key 발급
        
        Returns:
            str: Approval key
            
        Raises:
            Exception: 인증 실패 시
        """
        url = f"{KIS_BASE_URL}/oauth2/Approval"
        headers = {"content-type": "application/json; utf-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": APP_KEY,
            "secretkey": APP_SECRET
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
                data = await resp.json()
                if "approval_key" in data:
                    self.approval_key = data["approval_key"]
                    logger.info("✅ KIS Approval key obtained")
                    return self.approval_key
                else:
                    logger.error(f"Failed to get approval key: {data}")
                    raise Exception("KIS Auth Failed")
    
    async def get_access_token(self) -> str:
        """
        KIS REST API 접속을 위한 OAuth Access Token 발급
        """
        url = f"{KIS_BASE_URL}/oauth2/tokenP"
        headers = {"content-type": "application/json; utf-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
                data = await resp.json()
                if "access_token" in data:
                    token = data["access_token"]
                    logger.info("✅ KIS Access Token obtained")
                    return token
                else:
                    logger.error(f"Failed to get access token: {data}")
                    raise Exception(f"KIS REST Auth Failed: {data}")

    def reset_key(self):
        """Approval key 초기화 (재발급 유도)"""
        self.approval_key = None
        logger.info("🔄 Approval key reset")
