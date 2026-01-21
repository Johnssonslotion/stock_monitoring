"""
[RFC-007] KIS Service Entry Point
Unified KIS Collector for KR & US Markets (Single Key Management)
"""
import asyncio
import logging
import os
import sys
import json
from datetime import datetime, time, timedelta
import pytz
import redis.asyncio as redis

from src.data_ingestion.price.common import KISAuthManager
from src.data_ingestion.price.common.websocket_dual import DualWebSocketManager
from src.data_ingestion.price.kr.real_collector import KRRealCollector
from src.data_ingestion.price.us.real_collector import USRealCollector
from src.data_ingestion.price.kr.asp_collector import KRASPCollector
from src.data_ingestion.price.us.asp_collector import USASPCollector

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KIS-Service")

# Environment Variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KIS_WS_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:21000")

# Timezone
TZ_KST = pytz.timezone('Asia/Seoul')
auth_manager = KISAuthManager()

async def schedule_key_refresh(manager):
    """
    일일 Approval Key 갱신 스케줄러 (Unified Copy)
    """
    while True:
        try:
            now_kst = datetime.now(TZ_KST)
            kr_refresh = now_kst.replace(hour=8, minute=0, second=0, microsecond=0)
            us_refresh = now_kst.replace(hour=22, minute=0, second=0, microsecond=0)
            
            candidates = []
            if kr_refresh > now_kst: candidates.append(kr_refresh)
            else: candidates.append(kr_refresh + timedelta(days=1))
            
            if us_refresh > now_kst: candidates.append(us_refresh)
            else: candidates.append(us_refresh + timedelta(days=1))
            
            next_refresh = min(candidates)
            wait_seconds = (next_refresh - now_kst).total_seconds()
            
            logger.info(f"⏰ Next API key refresh: {next_refresh.strftime('%Y-%m-%d %H:%M')} KST")
            await asyncio.sleep(wait_seconds)
            
            logger.warning(f"🔑 [SCHEDULED] API Key Refresh at {next_refresh.strftime('%H:%M')}")
            new_key = await auth_manager.get_approval_key()
            if hasattr(manager, 'approval_key'):
                manager.approval_key = new_key
            
            # Alert
            r = await redis.from_url(REDIS_URL, decode_responses=True)
            await r.publish("system:alerts", json.dumps({
                "timestamp": datetime.now(TZ_KST).isoformat(),
                "level": "INFO",
                "message": f"✅ API Key Refreshed at {next_refresh.strftime('%H:%M')} KST"
            }))
            await r.aclose()
            
        except Exception as e:
            logger.error(f"Key refresh scheduler error: {e}")
            await asyncio.sleep(300)

async def market_scheduler(manager):
    """
    시장 시간 기반 동적 구독 스케줄러 (KR <-> US)
    """
    logger.info("📅 Market Scheduler Started (KIS Unified)")
    current_mode = None 
    
    while True:
        try:
            now_kst = datetime.now(TZ_KST)
            current_time = now_kst.time()
            
            # KR: 08:30 ~ 16:00
            kr_start, kr_end = time(8, 30), time(16, 0)
            # US: 17:00 ~ 08:00 (Next Day)
            us_start, us_end = time(17, 0), time(8, 0)
            
            is_kr_time = check_time_cross_midnight(current_time, kr_start, kr_end)
            is_us_time = check_time_cross_midnight(current_time, us_start, us_end)
            
            if is_kr_time:
                if current_mode != 'KR':
                    logger.info("🔁 Market Switch: US/Idle -> KR")
                    await manager.switch_urls(
                        f"{KIS_WS_URL}/H0STCNT0",
                        f"{KIS_WS_URL}/H0STASP0"
                    )
                    current_mode = 'KR'
                if 'KR' not in manager.active_markets:
                     await manager.subscribe_market('KR')

            elif is_us_time:
                if current_mode != 'US':
                    logger.info("🔁 Market Switch: KR/Idle -> US")
                    # US Start Policy: Refresh Key
                    try:
                        new_key = await auth_manager.get_approval_key()
                        await manager.update_key(new_key)
                    except Exception as e:
                        logger.error(f"US Start Key Refresh Failed: {e}")

                    await manager.switch_urls(
                        f"{KIS_WS_URL}/HDFSCNT0",
                        f"{KIS_WS_URL}/HDFSASP0"
                    )
                    current_mode = 'US'
                if 'US' not in manager.active_markets:
                    await manager.subscribe_market('US')
            else:
                # Idle
                pass
                
        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
            await asyncio.sleep(5)
        
        await asyncio.sleep(10)

def check_time_cross_midnight(current: time, start: time, end: time) -> bool:
    if start < end:
        return start <= current <= end
    else:
        return start <= current or current <= end

async def main():
    logger.info("🚀 Starting KIS Unified Service (RFC-007 Isolated)...")
    
    # 1. Approval Key
    approval_key = await auth_manager.get_approval_key()
    
    # 2. Collectors (Tick Only for Stability)
    # Explicitly set config paths to avoid env var override conflicts
    kr_tick = KRRealCollector(config_path="configs/kr_symbols.yaml")
    us_tick = USRealCollector(config_path="configs/us_symbols.yaml")
    # kr_hoga = KRASPCollector()  # Disabled for single-socket stability
    # us_hoga = USASPCollector()
    
    # 3. Manager
    manager = DualWebSocketManager(
        collectors=[kr_tick, us_tick],
        redis_url=REDIS_URL
    )
    
    # 4. Auto-Refresh Callback
    async def refresh_logic():
        logger.warning("♻️  Reactive Key Refresh Triggered!")
        try:
            new_key = await auth_manager.get_approval_key()
            await manager.update_key(new_key)
        except Exception as e:
            logger.error(f"Failed to auto-refresh key: {e}")

    manager.set_refresh_callback(refresh_logic)
    
    # 5. Tasks
    asyncio.create_task(market_scheduler(manager))
    asyncio.create_task(schedule_key_refresh(manager))
    
    # 6. Run
    # Determine initial market based on current time
    now_kst = datetime.now(TZ_KST).time()
    kr_start, kr_end = time(8, 30), time(16, 0)
    
    if check_time_cross_midnight(now_kst, kr_start, kr_end):
        tick_url = f"{KIS_WS_URL}/H0STCNT0"
        orderbook_url = f"{KIS_WS_URL}/H0STASP0"
    else:
        tick_url = f"{KIS_WS_URL}/HDFSCNT0"
        orderbook_url = f"{KIS_WS_URL}/HDFSASP0"
        
    await manager.run(tick_url, orderbook_url, approval_key)

if __name__ == "__main__":
    asyncio.run(main())
