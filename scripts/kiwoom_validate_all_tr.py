#!/usr/bin/env python3
"""
Kiwoom WebSocket - 전체 TR 타입 검증
"""
import asyncio
import os
import json
import logging
from dotenv import load_dotenv
import websockets
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Kiwoom")

load_dotenv(".env.backtest")

KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")

# 공식 문서의 모든 TR 타입
ALL_TR_TYPES = {
    "00": "주문체결",
    "04": "잔고",
    "0A": "주식기세",
    "0B": "주식체결",
    "0C": "주식우선호가",
    "0D": "주식호가잔량",
    "0E": "주식시간외호가",
    "0F": "주식당일거래원",
    "0G": "ETF NAV",
    "0H": "주식예상체결",
    "0I": "국제금환산가격",
    "0J": "업종지수",
    "0U": "업종등락",
    "0g": "주식종목정보",
    "0m": "ELW 이론가",
    "0s": "장시작시간",
    "0u": "ELW 지표",
    "0w": "종목프로그램매매",
    "1h": "VI발동/해제"
}

async def get_token():
    async with aiohttp.ClientSession() as session:
        url = "https://api.kiwoom.com/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey": KIWOOM_APP_KEY,
            "secretkey": KIWOOM_APP_SECRET
        }
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        
        async with session.post(url, json=payload, headers=headers, ssl=False) as resp:
            data = await resp.json()
            return data.get("token")

async def main():
    token = await get_token()
    logger.info(f"✅ Token: {token[:15]}...\n")
    
    ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    
    async with websockets.connect(ws_url) as ws:
        logger.info("✅ WebSocket Connected!")
        
        # LOGIN
        await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
        response = await ws.recv()
        logger.info(f"📥 LOGIN: {response}\n")
        
        # 테스트용 종목들
        stock_symbols = ["005930", "000660", "035720"]  # 삼성, SK하이닉스, 카카오
        index_symbols = ["0001", "1001"]  # 코스피, 코스닥
        
        # 테스트 결과 저장
        results = {}
        
        logger.info("="*80)
        logger.info("전체 TR 타입 검증 시작")
        logger.info("="*80 + "\n")
        
        for tr_code, tr_name in ALL_TR_TYPES.items():
            logger.info(f"[{tr_code}] {tr_name}")
            logger.info("-" * 40)
            
            # 업종 관련은 업종 코드 사용
            if tr_code in ["0J", "0U"]:
                symbols = index_symbols
            else:
                symbols = stock_symbols
            
            # 그룹 번호를 TR 코드 기반으로 생성 (숫자만)
            grp_no = f"{ord(tr_code[0]):03d}{ord(tr_code[1]):01d}"[:4]
            
            reg_msg = {
                "trnm": "REG",
                "grp_no": grp_no,
                "refresh": "1",
                "data": [
                    {
                        "item": symbols,
                        "type": [tr_code]
                    }
                ]
            }
            
            await ws.send(json.dumps(reg_msg))
            logger.info(f"   📤 REG 전송 (grp_no: {grp_no})")
            
            # 응답 대기
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(response)
                
                return_code = data.get("return_code")
                return_msg = data.get("return_msg", "")
                
                if return_code == 0:
                    results[tr_code] = "✅ SUCCESS"
                    logger.info(f"   ✅ 성공")
                else:
                    results[tr_code] = f"❌ FAILED ({return_code})"
                    logger.info(f"   ❌ 실패: [{return_code}] {return_msg}")
                    
            except asyncio.TimeoutError:
                results[tr_code] = "⏰ TIMEOUT"
                logger.info(f"   ⏰ 응답 없음")
            except Exception as e:
                results[tr_code] = f"❌ ERROR: {str(e)}"
                logger.info(f"   ❌ 에러: {e}")
            
            logger.info("")
            await asyncio.sleep(0.3)
        
        # 최종 요약
        logger.info("="*80)
        logger.info("검증 결과 요약")
        logger.info("="*80 + "\n")
        
        success_count = 0
        failed_count = 0
        
        for tr_code, tr_name in ALL_TR_TYPES.items():
            status = results.get(tr_code, "미검증")
            logger.info(f"{tr_code:3s} | {tr_name:20s} | {status}")
            
            if "SUCCESS" in status:
                success_count += 1
            elif "FAILED" in status or "ERROR" in status:
                failed_count += 1
        
        logger.info("\n" + "="*80)
        logger.info(f"총 {len(ALL_TR_TYPES)}개 중: ✅ {success_count}개 성공, ❌ {failed_count}개 실패")
        logger.info("="*80)
        
        # 결과를 JSON 파일로 저장
        with open("kiwoom_tr_validation_results.json", "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": "2026-01-16T13:40:00",
                "total": len(ALL_TR_TYPES),
                "success": success_count,
                "failed": failed_count,
                "details": {
                    tr_code: {
                        "name": tr_name,
                        "status": results.get(tr_code, "미검증")
                    }
                    for tr_code, tr_name in ALL_TR_TYPES.items()
                }
            }, f, ensure_ascii=False, indent=2)
        
        logger.info("\n📄 Result saved: kiwoom_tr_validation_results.json")

if __name__ == "__main__":
    asyncio.run(main())
