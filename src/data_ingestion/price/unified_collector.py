"""
KR/US 통합 실시간 수집기 엔트리포인트 (Unified Realtime Collector)
- Dual-Socket Architecture 적용: Tick과 Orderbook 소켓 분리
- *Dynamic Subscription*: 시간대에 따라 KR/US 구독을 스위칭
"""
import asyncio
import logging
import os
from datetime import datetime, time
import pytz

from src.data_ingestion.price.common import KISAuthManager
from src.data_ingestion.price.common.websocket_dual import DualWebSocketManager
from src.data_ingestion.price.common.websocket_base import UnifiedWebSocketManager
import redis.asyncio as redis
import json
import sys
from src.data_ingestion.price.kr.real_collector import KRRealCollector
from src.data_ingestion.price.us.real_collector import USRealCollector
from src.data_ingestion.price.kr.asp_collector import KRASPCollector
from src.data_ingestion.price.us.asp_collector import USASPCollector

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("UnifiedCollector")

# 환경 변수
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KIS_WS_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:21000")

# 인증 관리자
auth_manager = KISAuthManager()
TZ_KST = pytz.timezone('Asia/Seoul')

async def schedule_key_refresh(manager):
    """일일 Approval Key 갱신 스케줄러"""
    # NOTE: Simplistic implementation, can be enhanced later
    pass

async def market_scheduler(manager: DualWebSocketManager):
    """
    시장 시간 기반 동적 구독 스케줄러 (Dual-Socket Aware)
    """
    logger.info("📅 Market Scheduler Started")
    
    current_mode = None 
    
    while True:
        try:
            now_kst = datetime.now(TZ_KST)
            current_time = now_kst.time()
            
            # KR Market: 08:30 ~ 16:00 KST
            kr_start = time(8, 30)
            kr_end = time(16, 0)
            
            # US Market: 17:00 ~ 08:00 KST (Next Day) - Expanded range
            us_start = time(17, 0)
            us_end = time(8, 0)
            
            is_kr_time = check_time_cross_midnight(current_time, kr_start, kr_end)
            is_us_time = check_time_cross_midnight(current_time, us_start, us_end)
            
            # Dynamic URL Switching Logic
            if is_kr_time:
                # Switch to KR Mode
                if current_mode != 'KR':
                    logger.info("🔁 Market Switch Detected: US/Idle -> KR")
                    kr_url = f"{KIS_WS_URL}/H0STCNT0" # Use Tick Endpoint as Base
                    await manager.switch_url(kr_url)
                    current_mode = 'KR'
                
                # Subscription Check (Idempotent)
                if 'KR' not in manager.active_markets:
                     # Wait for socket availability implicitly handled by manager retry
                     await manager.subscribe_market('KR')

            elif is_us_time:
                # Switch to US Mode
                if current_mode != 'US':
                    logger.info("🔁 Market Switch Detected: KR/Idle -> US")
                    us_url = f"{KIS_WS_URL}/HDFSCNT0" # Use Tick Endpoint as Base
                    await manager.switch_url(us_url)
                    current_mode = 'US'
                
                # Subscription Check
                if 'US' not in manager.active_markets:
                    await manager.subscribe_market('US')
            else:
                # Idle Time
                pass
                
        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
        
        await asyncio.sleep(10)

def check_time_cross_midnight(current: time, start: time, end: time) -> bool:
    if start < end:
        return start <= current <= end
    else: # Cross midnight
        return start <= current or current <= end

async def main():
    logger.info("🚀 Starting Unified Real-time Collector (Dual-Socket Mode)...")

    # 1. Approval Key 발급
    approval_key = await auth_manager.get_approval_key()
    
    # 2. 수집기 인스턴스 생성 (KR/US Tick & Orderbook)
    kr_tick = KRRealCollector()
    kr_hoga = KRASPCollector()
    us_tick = USRealCollector()
    us_hoga = USASPCollector()
    
    # 3. Mode Selection (Doomsday Protocol)
    # Check Redis Config
    r = await redis.from_url(REDIS_URL, decode_responses=True)
    enable_dual = await r.get("config:enable_dual_socket")
    await r.close()
    
    use_dual = enable_dual is None or enable_dual.lower() == 'true'
    
    manager = None
    if use_dual:
        logger.info("⚔️  Mode: DUAL SOCKET (High Performance)")
        manager = DualWebSocketManager(
            collectors=[kr_tick, kr_hoga, us_tick, us_hoga],
            redis_url=REDIS_URL
        )
    else:
        logger.warning("🛡️  Mode: SINGLE SOCKET (Safe Mode)")
        manager = UnifiedWebSocketManager(
            collectors=[kr_tick, kr_hoga, us_tick, us_hoga],
            redis_url=REDIS_URL
        )

    # 3.5 Suicide Packet Listener
    async def kill_switch_listener():
        client = await redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe("system:control")
        logger.info("📡 Listening for Suicide Packets on 'system:control'...")
        async for msg in pubsub.listen():
            if msg['type'] == 'message':
                try:
                    data = json.loads(msg['data'])
                    if data.get('command') == 'restart':
                        logger.critical(f"💀 SUICIDE PACKET RECEIVED: {data.get('reason')}")
                        logger.critical("👋 Goodbye. (Triggering Docker Restart)")
                        sys.exit(1)
                except Exception as e:
                    logger.error(f"Kill Switch Error: {e}")

    asyncio.create_task(kill_switch_listener())
    
    # Default URL (will be corrected by scheduler immediately)
    ws_url = f"{KIS_WS_URL}/HDFSCNT0"

    # 4. 실행 (WebSocket Loop + Scheduler)
    asyncio.create_task(market_scheduler(manager))
    
    await manager.run(ws_url, approval_key)

if __name__ == "__main__":
    asyncio.run(main())
