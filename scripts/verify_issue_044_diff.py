import asyncio
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import asyncpg
from src.api_gateway.hub.client import APIHubClient
from src.api_gateway.hub.tr_registry import UseCase, get_tr_id_for_use_case

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyFixedGap")

async def main():
    # 1. Connect to DB and API Hub
    # Fix: Use localhost for running from shell
    db_url = os.getenv("TIMESCALE_URL", "postgresql://postgres:password@localhost:5432/stockval")
    hub_client = APIHubClient()
    
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        logger.error(f"❌ DB Connection failed: {e}")
        return

    symbol = "005930" # Samsung Electronics
    today = datetime.now().strftime("%Y%m%d")
    
    logger.info(f"🔍 Verifying Ground Truth for {symbol} on {today}...")

    # 2. Fetch DB Data (Continuous Aggregate View)
    logger.info("1️⃣ Fetching Aggregated View (market_candles_1m_view)...")
    try:
        rows = await conn.fetch("""
            SELECT time, open, high, low, close, volume 
            FROM market_candles_1m_view 
            WHERE symbol = $1 
            ORDER BY time DESC 
            LIMIT 60
        """, symbol)
    except Exception as e:
        logger.error(f"❌ Failed to query DB View: {e}")
        await conn.close()
        return
    
    db_data = {r['time'].strftime("%H%M"): r for r in rows}
    logger.info(f"   => Found {len(db_data)} minutes in DB View.")

    # 3. Fetch Ground Truth (KIS REST API)
    logger.info("2️⃣ Fetching Ground Truth (KIS API)...")
    tr_id = get_tr_id_for_use_case(UseCase.MINUTE_CANDLE_KIS)
    
    # Needs REDIS_URL for Hub Client? Default is localhost:6379/15 which is correct.
    try:
        result = await hub_client.execute(
            provider="KIS",
            tr_id=tr_id,
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": "", # Current time
                "FID_PW_DATA_INCU_YN": "Y"
            }
        )
    except Exception as e:
        logger.error(f"❌ API Hub Client Error: {e}")
        await conn.close()
        return
    
    api_data = {}
    if result.get('status') == 'SUCCESS':
        items = result['data']['output2']
        logger.info(f"   => Found {len(items)} minutes from KIS API.")
        for item in items:
            t = item['stck_cntg_hour'] # HHMMSS
            time_key = t[:4]
            api_data[time_key] = {
                'open': float(item['stck_oprc']),
                'high': float(item['stck_hgpr']),
                'low': float(item['stck_lwpr']),
                'close': float(item['stck_prpr']),
                'volume': int(item['cntg_vol'])
            }
    else:
        logger.error(f"❌ Failed to fetch API data: {result}")
        await conn.close()
        return

    # 4. Compare
    logger.info("3️⃣ Comparing Results...")
    matches = 0
    mismatches = 0
    
    print("\n[Comparison Result (Last 10 minutes)]")
    print(f"{'Time':<6} | {'DB Vol':<8} | {'API Vol':<8} | {'Diff':<8} | {'Status'}")
    print("-" * 50)
    
    # Compare overlapping keys
    common_keys = sorted(set(db_data.keys()) & set(api_data.keys()), reverse=True)
    
    if not common_keys:
        logger.warning("⚠️ No overlapping timestamp keys found.")
    
    for k in common_keys[:10]: # Show last 10
        db_vol = int(db_data[k]['volume'])
        api_vol = int(api_data[k]['volume'])
        diff = abs(db_vol - api_vol)
        status = "✅" if diff == 0 else ("⚠️" if diff < api_vol * 0.01 else "❌")
        
        print(f"{k:<6} | {db_vol:<8} | {api_vol:<8} | {diff:<8} | {status}")
        
        if status == "✅":
            matches += 1
        else:
            mismatches += 1

    total_checked = len(common_keys)
    match_rate = (matches / total_checked * 100) if total_checked > 0 else 0
    logger.info(f"\n📊 Summary: {matches}/{total_checked} Matched ({match_rate:.1f}%)")
    
    await conn.close()
    await hub_client.close()

if __name__ == "__main__":
    asyncio.run(main())
