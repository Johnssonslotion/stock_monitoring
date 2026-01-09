"""
KR/US 통합 실시간 수집기 엔트리포인트 (Unified Realtime Collector)
- 단일 WebSocket 연결로 KR, US 시장 데이터를 동시에 수집
- *Dynamic Subscription*: 시간대에 따라 KR/US 구독을 스위칭하여 40개 제한 회피
"""
import asyncio
import logging
import os
from datetime import datetime, time
import pytz

from src.data_ingestion.price.common import KISAuthManager
from src.data_ingestion.price.common.websocket_base import UnifiedWebSocketManager
from src.data_ingestion.price.kr.real_collector import KRRealCollector
from src.data_ingestion.price.us.real_collector import USRealCollector
from src.data_ingestion.price.kr.asp_collector import KRASPCollector
# from src.data_ingestion.price.us.asp_collector import USASPCollector # Disabled

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("UnifiedCollector")

# 환경 변수
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KIS_WS_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:21000")

# 인증 관리자
auth_manager = KISAuthManager()
TZ_KST = pytz.timezone('Asia/Seoul')
TZ_US = pytz.timezone('America/New_York')

async def schedule_key_refresh():
    """일일 Approval Key 갱신 스케줄러"""
    while True:
        await asyncio.sleep(3600) # Simple 1h check for now or implement exact time logic
        # For MVP, just keep key valid. 
        # KIS keys are valid for 24h. Restarting container daily is easier strategy.
        pass

async def market_scheduler(manager: UnifiedWebSocketManager):
    """
    시장 시간 기반 동적 구독 스케줄러
    - KR Open (09:00 ~ 15:30 KST) -> Subscribe KR, Unsubscribe US
    - US Open (09:30 ~ 16:00 EST) -> Subscribe US, Unsubscribe KR
    - Gap -> Keep previous or Unsubscribe all?
    - Simplification: 
      - If 08:30 <= KST <= 16:00: KR Mode
      - If 21:00 <= KST <= 06:00 (Next Day): US Mode
    """
    logger.info("📅 Market Scheduler Started")
    
    last_refresh_time = datetime.min.replace(tzinfo=TZ_KST)
    
    while True:
        try:
            now_kst = datetime.now(TZ_KST)
            current_time = now_kst.time()
            
            # --- Key Refresh Logic (08:30 / 23:00 KST) ---
            # 장 시작 30분 전 예열 (Warm-up)
            # 강력한 갱신: 08:30:00 ~ 08:30:59, 23:00:00 ~ 23:00:59 범위 체크
            refresh_targets = [(8, 30), (23, 0)]
            for hour, minute in refresh_targets:
                # 현재 시각이 목표 시간대(분)에 있는지 확인
                if current_time.hour == hour and current_time.minute == minute:
                    # 마지막 갱신 후 1시간 이상 경과 시 실행 (중복 방지)
                    time_since_last = (now_kst - last_refresh_time).total_seconds()
                    if time_since_last > 3600:
                        logger.info(f"🔄 Scheduled Key Refresh TRIGGERED at {now_kst.strftime('%H:%M:%S')}")
                        logger.info(f"   Last refresh was {time_since_last/3600:.1f} hours ago")
                        try:
                            new_key = await auth_manager.get_approval_key()
                            await manager.update_key(new_key)
                            last_refresh_time = now_kst
                            logger.info(f"🔑 Scheduled Key Refresh COMPLETE at {hour:02d}:{minute:02d}")
                        except Exception as e:
                            logger.error(f"❌ Key Refresh FAILED: {e}")
                    else:
                        logger.debug(f"⏭️  Key refresh skipped (last: {time_since_last:.0f}s ago)")
            # -----------------------------------------------
            
            # 주말/공휴일 체크는 생략 (Simplicity)
            
            # Note: Docker Container TZ is set to Asia/Seoul.
            # KR Market: 08:30 ~ 16:00 KST
            kr_start = time(8, 30)
            kr_end = time(16, 0)
            
            # US Market: 17:00 ~ 06:00 KST (Pre-Market 18:00 includes buffer)
            us_start = time(17, 0)
            us_end = time(6, 0)
            
            # KR doesn't cross midnight
            is_kr_time = check_time_cross_midnight(current_time, kr_start, kr_end)
            # US crosses midnight (17:00 -> 06:00)
            is_us_time = check_time_cross_midnight(current_time, us_start, us_end)
            
            logger.info(f"⏰ Time Check: {current_time} (KST) | KR: {is_kr_time} | US: {is_us_time} | Active: {manager.active_markets}")

            if is_kr_time:
                # KR Mode
                if 'US' in manager.active_markets:
                    await manager.unsubscribe_market('US')
                if 'KR' not in manager.active_markets:
                    # WebSocket 연결 대기 (manager.websocket is None이면 내부에서 return함)
                    if manager.websocket:
                        await manager.subscribe_market('KR')
                    else:
                        logger.warning("WebSocket not ready yet for KR sub")
                        
            elif is_us_time:
                # US Mode
                if 'KR' in manager.active_markets:
                    await manager.unsubscribe_market('KR')
                if 'US' not in manager.active_markets:
                    if manager.websocket:
                        await manager.subscribe_market('US')
                    else:
                        logger.warning("WebSocket not ready yet for US sub")
            else:
                # Idle Time (Neither KR nor US)
                # Keep current state? Or Unsubscribe All?
                # To be safe against 24h key expiry, maybe safer to Keep current?
                # But to save resources, Unsubscribe All might be better.
                # Let's default to US Mode if ambiguous (since we develop mostly at night in KR)
                # OR just keep checking.
                pass
                
        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
        
        await asyncio.sleep(10) # Check every 10s

def check_time_cross_midnight(current: time, start: time, end: time) -> bool:
    if start < end:
        return start <= current <= end
    else: # Cross midnight
        return start <= current or current <= end

async def main():
    # 1. Approval Key 발급
    approval_key = await auth_manager.get_approval_key()
    
    # 2. 수집기 인스턴스 생성
    kr_collector = KRRealCollector()
    us_collector = USRealCollector()
    kr_asp = KRASPCollector()
    # us_asp = USASPCollector() # Disabled
    
    # 3. 통합 매니저 생성
    manager = UnifiedWebSocketManager(
        collectors=[kr_collector, us_collector, kr_asp],
        redis_url=REDIS_URL
    )
    
    # PRODUCTION WebSocket URL (NOT /tryitout/ test endpoint)
    ws_url = f"{KIS_WS_URL}/H0STCNT0"

    logger.info(f"Starting Unified Collector with {ws_url}")
    
    # 4. 실행 (WebSocket Loop + Scheduler)
    # create_task for background tasks
    asyncio.create_task(market_scheduler(manager))
    
    await manager.run(ws_url, approval_key)

if __name__ == "__main__":
    asyncio.run(main())
