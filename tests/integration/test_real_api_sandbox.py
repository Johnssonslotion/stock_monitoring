"""
HUB-INT-02: Real API Sandbox Integration Test

이 테스트는 KIS/Kiwoom 샌드박스 API와의 실제 통신을 검증합니다.
TokenManager의 Redlock 및 자동 갱신 로직이 실제 환경에서 작동하는지 확인합니다.

⚠️ 유효한 API Key가 .env.prod에 설정되어 있어야 합니다.
실행 방법: PYTHONPATH=. poetry run pytest -m manual tests/integration/test_real_api_sandbox.py
"""
import pytest
import asyncio
import os
import logging
from dotenv import load_dotenv
from redis.asyncio import Redis
from src.api_gateway.hub.token_manager import TokenManager
from src.api_gateway.hub.clients.kis_client import KISClient
from src.api_gateway.hub.clients.kiwoom_client import KiwoomClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRealApiSandbox")

# .env.prod 로드
load_dotenv(".env.prod")

@pytest.mark.manual
@pytest.mark.asyncio
async def test_kis_real_api_sandbox():
    """KIS 샌드박스 API 통합 테스트"""
    redis_url = os.getenv("REDIS_URL_HUB", "redis://localhost:6379/15")
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    try:
        # 1. Setup TokenManager
        token_manager = TokenManager(redis_client=redis)
        
        # 2. Setup Client
        client = KISClient(token_manager=token_manager)
        logger.info(f"🚀 Testing KIS Sandbox at {client.base_url}")
        
        # 3. API 호출 (국내주식 시세 - 삼성전자)
        tr_id = "FHKST01010100"
        params = {"symbol": "005930"}
        
        result = await client.execute(tr_id=tr_id, params=params)
        
        # 4. 검증
        assert result["status"] == "success"
        assert result["provider"] == "KIS"
        assert "data" in result
        
        logger.info(f"✅ KIS Sandbox Data: {str(result['data'])[:100]}...")
        
        # Redis에 토큰이 저장되었는지 확인
        token_exists = await redis.exists("api:token:kis")
        assert token_exists, "Token should be cached in Redis"
        
    finally:
        await redis.aclose()

@pytest.mark.manual
@pytest.mark.asyncio
async def test_kiwoom_real_api_sandbox():
    """Kiwoom 샌드박스 API 통합 테스트"""
    redis_url = os.getenv("REDIS_URL_HUB", "redis://localhost:6379/15")
    redis = await Redis.from_url(redis_url, decode_responses=True)
    
    try:
        # 1. Setup TokenManager
        token_manager = TokenManager(redis_client=redis)
        
        # 2. Setup Client
        client = KiwoomClient(token_manager=token_manager)
        logger.info(f"🚀 Testing Kiwoom Sandbox at {client.base_url}")
        
        # 3. API 호출 (주식분봉조회 - 삼성전자)
        tr_id = "opt10081"
        params = {"symbol": "005930"}
        
        result = await client.execute(tr_id=tr_id, params=params)
        
        # 4. 검증
        assert result["status"] == "success"
        assert result["provider"] == "KIWOOM"
        assert "data" in result
        
        logger.info(f"✅ Kiwoom Sandbox Data: {str(result['data'])[:100]}...")
        
        # Redis에 토큰이 저장되었는지 확인
        token_exists = await redis.exists("api:token:kiwoom")
        assert token_exists, "Token should be cached in Redis"
        
    finally:
        await redis.aclose()

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "-m", "manual"]))
