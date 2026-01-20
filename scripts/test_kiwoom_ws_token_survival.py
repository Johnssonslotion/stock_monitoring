#!/usr/bin/env python3
"""
Kiwoom WS Token Survival Test
=============================
목적: WS 연결 상태에서 새 토큰 발급 시 기존 WS 세션이 유지되는지 검증

테스트 시나리오:
1. Token1 발급 → WS 연결 → LOGIN 성공
2. WS 연결 유지한 상태에서 Token2 발급 (REST용)
3. Token2로 REST API 호출
4. 기존 WS 세션이 여전히 데이터 수신 가능한지 확인

결과 해석:
- WS 유지됨: 분리 운영 가능 (WS/REST 독립 토큰)
- WS 끊김: 토큰 공유 필수 (동기화 갱신 필요)
"""
import asyncio
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
import websockets

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("KiwoomWSSurvival")

load_dotenv(".env")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")

TOKEN_URL = "https://api.kiwoom.com/oauth2/token"
REST_URL = "https://api.kiwoom.com/api/dostk/chart"
WS_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"


async def get_token(session: aiohttp.ClientSession, label: str) -> str:
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
        if token:
            logger.info(f"✅ {label}: {token[:15]}...")
            return token
        else:
            logger.error(f"❌ {label} 실패: {data}")
            return None


async def test_rest_api(session: aiohttp.ClientSession, token: str, label: str) -> bool:
    """REST API 호출 테스트"""
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10079",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    body = {
        "stk_cd": "005930",
        "tic_scope": "1",
        "upd_stkpc_tp": "0"
    }

    try:
        async with session.post(REST_URL, json=body, headers=headers) as resp:
            data = await resp.json()
            if data.get("return_code") == 0:
                logger.info(f"✅ {label} REST 성공")
                return True
            else:
                logger.warning(f"⚠️ {label} REST 실패: {data.get('return_msg')}")
                return False
    except Exception as e:
        logger.error(f"❌ {label} REST 예외: {e}")
        return False


async def main():
    print("=" * 60)
    print("Kiwoom WS Token Survival Test")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().isoformat()}")
    print()

    async with aiohttp.ClientSession() as http_session:
        # Step 1: WS용 토큰 발급
        print("[Step 1] WS용 Token 발급")
        ws_token = await get_token(http_session, "WS-Token")
        if not ws_token:
            return

        # Step 2: WS 연결 및 LOGIN
        print("\n[Step 2] WebSocket 연결 및 LOGIN")
        try:
            ws = await websockets.connect(WS_URL)
            logger.info("✅ WS 연결 성공")

            # LOGIN
            login_msg = {"trnm": "LOGIN", "token": ws_token}
            await ws.send(json.dumps(login_msg))
            login_resp = await asyncio.wait_for(ws.recv(), timeout=5)
            login_data = json.loads(login_resp)

            if login_data.get("return_code") == 0:
                logger.info(f"✅ WS LOGIN 성공: {login_data}")
            else:
                logger.error(f"❌ WS LOGIN 실패: {login_data}")
                await ws.close()
                return

            # Step 3: WS 연결 유지 상태에서 REST용 토큰 발급
            print("\n[Step 3] WS 유지 상태에서 REST용 Token 발급")
            await asyncio.sleep(1)
            rest_token = await get_token(http_session, "REST-Token")

            print(f"\n[Token 비교]")
            print(f"  WS Token:   {ws_token[:25]}...")
            print(f"  REST Token: {rest_token[:25]}...")
            print(f"  동일 여부:  {ws_token == rest_token}")

            # Step 4: REST API 호출 (REST 토큰 사용)
            print("\n[Step 4] REST Token으로 API 호출")
            rest_success = await test_rest_api(http_session, rest_token, "REST-Token")

            # Step 5: WS 세션 생존 확인 (PING 또는 REG 시도)
            print("\n[Step 5] WS 세션 생존 확인")

            # 간단한 REG 요청으로 WS 세션 확인
            reg_msg = {
                "trnm": "REG",
                "grp_no": "9999",
                "refresh": "1",
                "data": [{"item": ["005930"], "type": ["0B"]}]
            }
            await ws.send(json.dumps(reg_msg))

            try:
                reg_resp = await asyncio.wait_for(ws.recv(), timeout=5)
                reg_data = json.loads(reg_resp)

                if reg_data.get("return_code") == 0:
                    logger.info(f"✅ WS 세션 생존 확인: REG 성공")
                    ws_survived = True
                else:
                    logger.warning(f"⚠️ WS 세션 문제: {reg_data}")
                    ws_survived = False
            except asyncio.TimeoutError:
                logger.warning("⚠️ WS 응답 없음 (Timeout)")
                ws_survived = False
            except websockets.exceptions.ConnectionClosed as e:
                logger.error(f"❌ WS 연결 끊김: {e}")
                ws_survived = False

            # 결과 분석
            print("\n" + "=" * 60)
            print("테스트 결과 분석")
            print("=" * 60)

            if ws_token == rest_token:
                print("📌 결과: 동일 토큰 반환")
                print("   → Kiwoom 서버가 토큰을 캐싱 (만료 전까지 동일)")
                print("   → WS/REST 자연스럽게 같은 토큰 공유")
                print("   → 소켓 오염 위험 없음 ✅")
            elif ws_survived:
                print("✅ 결과: 다른 토큰이지만 WS 세션 유지됨!")
                print("   → WS와 REST 독립 토큰 운영 가능")
                print("   → 각자 토큰 갱신해도 상호 영향 없음")
            else:
                print("❌ 결과: 새 토큰 발급 후 WS 세션 끊김")
                print("   → 토큰 갱신 시 WS 재연결 필요")
                print("   → 권장: 단일 토큰 관리자 패턴 사용")

            print(f"\n[상세 결과]")
            print(f"  REST API 호출: {'성공' if rest_success else '실패'}")
            print(f"  WS 세션 유지:  {'성공' if ws_survived else '실패'}")

            await ws.close()

        except Exception as e:
            logger.error(f"❌ WS 연결 실패: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
