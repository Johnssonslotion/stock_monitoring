#!/usr/bin/env python3
"""
API Hub Phase 2 - 실제 API 검증 스크립트

실제 KIS API 키로 토큰 발급 및 분봉 조회를 테스트합니다.
"""
import asyncio
import os
import sys
import logging

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logger = logging.getLogger("APIHubVerification")


async def verify_kis_token():
    """KIS 토큰 발급 검증"""
    from src.api_gateway.hub.clients.kis_client import KISClient
    
    logger.info("=" * 60)
    logger.info("🔑 KIS 토큰 발급 테스트")
    logger.info("=" * 60)
    
    try:
        client = KISClient()
        await client.connect()
        
        # 토큰 갱신
        token = await client.refresh_token()
        
        if token:
            logger.info(f"✅ KIS 토큰 발급 성공: {token[:20]}...")
            return token
        else:
            logger.error("❌ KIS 토큰 발급 실패")
            return None
    except Exception as e:
        logger.error(f"❌ KIS 토큰 에러: {e}")
        return None
    finally:
        await client.disconnect()


async def verify_kis_tick(access_token: str):
    """KIS Tick 조회 검증"""
    from src.api_gateway.hub.clients.kis_client import KISClient
    
    logger.info("=" * 60)
    logger.info("📊 KIS Tick 조회 테스트 (삼성전자 005930)")
    logger.info("=" * 60)
    
    try:
        client = KISClient(access_token=access_token)
        await client.connect()
        
        # 분봉 조회 (GET 요청)
        result = await client.execute(
            tr_id="FHKST01010300",  # Tick 조회 (BackfillManager와 동일)
            params={"symbol": "005930", "time": "153000"},
            method="GET"
        )
        
        if result["status"] == "success":
            data = result["data"]
            logger.info(f"✅ 분봉 조회 성공: {len(data)}건")
            
            if data:
                sample = data[0]
                logger.info(f"   - 체결시간: {sample.get('stck_cntg_hour')}")
                logger.info(f"   - 현재가: {sample.get('stck_prpr')}")
                logger.info(f"   - 체결량: {sample.get('cntg_vol')}")
            
            return True
        else:
            logger.error(f"❌ 분봉 조회 실패: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ 분봉 조회 에러: {e}")
        return False
    finally:
        await client.disconnect()


async def main():
    """메인 검증 루틴"""
    logger.info("🚀 API Hub Phase 2 - 실제 API 검증 시작")
    logger.info("")
    
    # 환경변수 확인
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    
    if not app_key or not app_secret:
        logger.error("❌ KIS_APP_KEY 또는 KIS_APP_SECRET 환경변수가 설정되지 않았습니다.")
        logger.info("   source .env.prod 후 다시 실행하세요.")
        return
    
    logger.info(f"✅ KIS_APP_KEY: {app_key[:10]}...")
    
    # 1. 토큰 발급 테스트
    token = await verify_kis_token()
    
    if not token:
        logger.error("토큰 발급 실패로 테스트 중단")
        return
    
    logger.info("")
    
    # 2. Tick 조회 테스트
    tick_ok = await verify_kis_tick(token)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 검증 결과 요약")
    logger.info("=" * 60)
    logger.info(f"   토큰 발급: {'✅ PASS' if token else '❌ FAIL'}")
    logger.info(f"   Tick 조회: {'✅ PASS' if tick_ok else '❌ FAIL'}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
