"""
KIS API 인증 관리 모듈 (KR/US 공용)
"""
import os
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

# Note: We fetch these inside methods to allow late loading (e.g. dotenv)
def get_kis_config():
    return {
        "base_url": os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443"),
        "app_key": os.getenv("KIS_APP_KEY"),
        "app_secret": os.getenv("KIS_APP_SECRET")
    }


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
        if self.approval_key:
            return self.approval_key

        config = get_kis_config()
        url = f"{config['base_url']}/oauth2/Approval"
        headers = {"content-type": "application/json; utf-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": config['app_key'],
            "secretkey": config['app_secret']
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
        KIS REST API 접속을 위한 OAuth Access Token 발급 (파일 캐싱 포함)
        """
        config = get_kis_config()
        token_cache_path = "data/kis_token.json"
        
        # 1. Check Cache
        if os.path.exists(token_cache_path):
            try:
                import json
                from datetime import datetime
                with open(token_cache_path, "r") as f:
                    cache = json.load(f)
                    # Check expiration (usually 24h, we use 23h for safety)
                    cached_at = datetime.fromisoformat(cache["created_at"])
                    if (datetime.now() - cached_at).total_seconds() < 3600 * 23:
                        logger.debug("✅ Using cached KIS Access Token")
                        return cache["access_token"]
            except Exception as e:
                logger.warning(f"Failed to read token cache: {e}")

        # 2. Fetch New Token
        url = f"{config['base_url']}/oauth2/tokenP"
        headers = {"content-type": "application/json; utf-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": config['app_key'],
            "appsecret": config['app_secret']
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
                data = await resp.json()
                if "access_token" in data:
                    token = data["access_token"]
                    logger.info("✅ KIS Access Token obtained and cached")
                    
                    # Save to Cache
                    try:
                        import json
                        from datetime import datetime
                        os.makedirs("data", exist_ok=True)
                        with open(token_cache_path, "w") as f:
                            json.dump({
                                "access_token": token,
                                "created_at": datetime.now().isoformat()
                            }, f)
                    except Exception as e:
                        logger.warning(f"Failed to save token cache: {e}")
                        
                    return token
                else:
                    logger.error(f"Failed to get access token: {data}")
                    raise Exception(f"KIS REST Auth Failed: {data}")

    async def verify_connectivity(self) -> bool:
        """
        API 키 유효성 및 서버 연결 상태 최소 레벨 검증
        """
        config = get_kis_config()
        logger.info(f"🔍 Verifying KIS Connectivity (Base: {config['base_url']})...")
        try:
            token = await self.get_access_token()
            if token:
                logger.info(f"✅ KIS Key is NORMAL. (Key starts with: {config['app_key'][:4]}...)")
                return True
        except Exception as e:
            logger.error(f"❌ KIS Connectivity Verification FAILED: {e}")
            return False
        return False

    def reset_key(self):
        """Approval key 초기화 (재발급 유도)"""
        self.approval_key = None
        logger.info("🔄 Approval key reset")
