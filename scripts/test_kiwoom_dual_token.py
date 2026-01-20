#!/usr/bin/env python3
"""
Kiwoom Dual Token Test
======================
목적: 동일 credentials로 2개 토큰 발급 시 첫 번째 토큰이 무효화되는지 검증

테스트 시나리오:
1. Token1 발급 → REST API 호출 성공 확인
2. Token2 발급 (1초 후)
3. Token1로 REST API 재호출 → 성공/실패?
4. Token2로 REST API 호출 → 성공 확인

결과 해석:
- Token1 유효: 분리 관리 가능 (WS용, REST용 별도)
- Token1 무효: 단일 토큰만 유효 (공유 필수)
"""
import asyncio
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("KiwoomDualToken")

load_dotenv(".env")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")

TOKEN_URL = "https://api.kiwoom.com/oauth2/token"
REST_URL = "https://api.kiwoom.com/api/dostk/chart"


async def get_token(session: aiohttp.ClientSession, label: str) -> dict:
    """토큰 발급"""
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIWOOM_APP_KEY,
        "secretkey": KIWOOM_APP_SECRET
    }
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
    }

    async with session.post(TOKEN_URL, json=payload, headers=headers) as resp:
        data = await resp.json()
        token = data.get("token")
        expires_dt = data.get("expires_dt")
        return_code = data.get("return_code")

        if return_code == 0 and token:
            logger.info(f"✅ {label} 발급 성공: {token[:15]}... (만료: {expires_dt})")
            return {"token": token, "expires_dt": expires_dt, "success": True}
        else:
            logger.error(f"❌ {label} 발급 실패: {data}")
            return {"token": None, "success": False, "error": data}


async def test_token_with_rest(session: aiohttp.ClientSession, token: str, label: str) -> dict:
    """토큰으로 REST API 호출 테스트 (ka10079 - 틱 차트)"""
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10079",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    body = {
        "stk_cd": "005930",  # 삼성전자
        "tic_scope": "1",
        "upd_stkpc_tp": "0"
    }

    try:
        async with session.post(REST_URL, json=body, headers=headers) as resp:
            status = resp.status
            data = await resp.json()

            return_code = data.get("return_code", -1)
            return_msg = data.get("return_msg", "")

            if status == 200 and return_code == 0:
                tick_count = len(data.get("stk_tic_chart_qry", []))
                logger.info(f"✅ {label} REST 호출 성공: {tick_count} ticks")
                return {"success": True, "status": status, "tick_count": tick_count}
            else:
                logger.warning(f"⚠️ {label} REST 호출 실패: HTTP {status}, code={return_code}, msg={return_msg}")
                return {"success": False, "status": status, "return_code": return_code, "return_msg": return_msg}

    except Exception as e:
        logger.error(f"❌ {label} REST 호출 예외: {e}")
        return {"success": False, "error": str(e)}


async def main():
    print("=" * 60)
    print("Kiwoom Dual Token Validity Test")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().isoformat()}")
    print()

    async with aiohttp.ClientSession() as session:
        # Step 1: Token1 발급
        print("[Step 1] Token1 발급")
        token1_result = await get_token(session, "Token1")
        if not token1_result["success"]:
            print("❌ Token1 발급 실패. 테스트 중단.")
            return
        token1 = token1_result["token"]

        # Step 2: Token1로 REST 호출 (기준선)
        print("\n[Step 2] Token1 유효성 확인 (기준선)")
        test1_baseline = await test_token_with_rest(session, token1, "Token1-기준")

        # Step 3: 1초 대기 후 Token2 발급
        print("\n[Step 3] 1초 대기 후 Token2 발급")
        await asyncio.sleep(1)
        token2_result = await get_token(session, "Token2")
        if not token2_result["success"]:
            print("❌ Token2 발급 실패. 테스트 중단.")
            return
        token2 = token2_result["token"]

        # Token 비교
        print(f"\n[Token 비교]")
        print(f"  Token1: {token1[:20]}...")
        print(f"  Token2: {token2[:20]}...")
        print(f"  동일 토큰: {token1 == token2}")

        # Step 4: Token1 재검증 (핵심 테스트)
        print("\n[Step 4] Token1 재검증 (Token2 발급 후)")
        test1_after = await test_token_with_rest(session, token1, "Token1-재검증")

        # Step 5: Token2 검증
        print("\n[Step 5] Token2 유효성 확인")
        test2 = await test_token_with_rest(session, token2, "Token2")

        # 결과 분석
        print("\n" + "=" * 60)
        print("테스트 결과 분석")
        print("=" * 60)

        if token1 == token2:
            print("⚠️ 결과: 동일 토큰 반환됨")
            print("   → Kiwoom은 동일 credentials에 대해 같은 토큰 반환")
            print("   → 분리 관리 불필요 (자연스럽게 공유됨)")
        elif test1_after["success"]:
            print("✅ 결과: Token1 여전히 유효!")
            print("   → 분리 관리 가능 (WS용/REST용 별도 발급 가능)")
            print("   → 권장: WS 연결 시 Token1, REST 호출 시 Token2 사용")
        else:
            print("❌ 결과: Token1 무효화됨")
            print(f"   → 에러: {test1_after.get('return_msg', test1_after)}")
            print("   → 분리 관리 불가 (단일 토큰만 유효)")
            print("   → 권장: 토큰 공유 + Rate Limit 강화")

        # 상세 결과
        print("\n[상세 결과]")
        print(f"  Token1 기준선: {'성공' if test1_baseline['success'] else '실패'}")
        print(f"  Token1 재검증: {'성공' if test1_after['success'] else '실패'}")
        print(f"  Token2 검증:   {'성공' if test2['success'] else '실패'}")


if __name__ == "__main__":
    asyncio.run(main())
