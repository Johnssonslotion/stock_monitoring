"""
Experiment: Tick Count Verification Feasibility Test

Tests whether 5-minute sampling can provide complete verification coverage
without exceeding Kiwoom API rate limits.

Strategy:
- Sample 5 minutes per hour (e.g., :00-:05, :15-:20, :30-:35, :45-:50)
- Total: ~32 minutes of 390-minute trading day = 8.2% coverage
- Assumption: If sampled intervals are clean, full day is likely clean
"""

import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Kiwoom API Configuration
KIWOOM_BASE_URL = "https://api.kiwoom.com"
KIWOOM_TOKEN = os.getenv("KIWOOM_TOKEN")


async def fetch_tick_count(session, symbol, start_time, end_time, retry_count=0):
    """
    Fetch tick count for a specific time window using ka10079 API.
    
    Returns:
        dict: {
            'symbol': str,
            'start': str,
            'end': str,
            'tick_count': int,
            'api_calls': int,
            'duration_ms': int,
            'rate_limited': bool
        }
    """
    url = f"{KIWOOM_BASE_URL}/api/dostk/chart"
    headers = {
        "authorization": f"Bearer {KIWOOM_TOKEN}",
        "api-id": "ka10079",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "cont-yn": "N"
    }
    
    body = {
        "stk_cd": symbol,
        "tic_scope": "1",  # 1 tick
        "upd_stkpc_tp": "0"
    }
    
    tick_count = 0
    api_calls = 0
    start = datetime.now()
    rate_limited = False
    
    try:
        while True:
            api_calls += 1
            async with session.post(url, headers=headers, json=body) as resp:
                # Handle rate limit with exponential backoff
                if resp.status == 429:
                    rate_limited = True
                    if retry_count < 3:
                        backoff = 2 ** retry_count  # 1s, 2s, 4s
                        print(f"⚠️ Rate Limited. Backing off {backoff}s...")
                        await asyncio.sleep(backoff)
                        return await fetch_tick_count(session, symbol, start_time, end_time, retry_count + 1)
                    else:
                        print(f"❌ Rate Limit exceeded after 3 retries")
                        break
                
                if resp.status != 200:
                    print(f"❌ API Error: {resp.status}")
                    break
                
                data = await resp.json()
                ticks = data.get("stk_tic_chart_qry", [])
                
                # Filter by time window
                filtered = [
                    t for t in ticks 
                    if start_time <= t['cntr_tm'] <= end_time
                ]
                
                tick_count += len(filtered)
                
                # Check for next page
                next_key = resp.headers.get("next-key")
                if not next_key or headers.get("cont-yn") == "Y":
                    break
                
                headers["cont-yn"] = "Y"
                headers["next-key"] = next_key
                
                # Increased rate limit protection
                await asyncio.sleep(1.0)  # 0.1 -> 1.0초
        
        duration = (datetime.now() - start).total_seconds() * 1000
        
        return {
            'symbol': symbol,
            'start': start_time,
            'end': end_time,
            'tick_count': tick_count,
            'api_calls': api_calls,
            'duration_ms': duration,
            'rate_limited': rate_limited
        }
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def run_5min_sampling_experiment(symbol="005930", date=None):
    """
    Test 5-minute sampling strategy for one trading day.
    
    Sampling intervals: Limited to 6 windows for initial test (to respect rate limits)
    """
    
    # Auto-set date to today if not specified
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    # Define sampling windows (HH:MM:SS format) - ONLY PAST HOURS for live testing
    # Current time: ~11:30 KST, so only test 09:00-11:30 windows
    sampling_windows = [
        ("090000", "090500"),  # 09:00-09:05 (Market open)
        ("091500", "092000"),  # 09:15-09:20
        ("093000", "093500"),  # 09:30-09:35
        ("100000", "100500"),  # 10:00-10:05
        ("103000", "103500"),  # 10:30-10:35
        ("110000", "110500"),  # 11:00-11:05
    ]
    
    print(f"🧪 Starting Tick Count Feasibility Experiment")
    print(f"Symbol: {symbol}")
    print(f"Date: {date}")
    print(f"Sampling Windows: {len(sampling_windows)}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        results = []
        total_ticks = 0
        total_api_calls = 0
        total_duration = 0
        rate_limited_count = 0
        
        for i, (start, end) in enumerate(sampling_windows, 1):
            print(f"\n[{i}/{len(sampling_windows)}] Testing window {start}-{end}...")
            
            result = await fetch_tick_count(session, symbol, start, end)
            
            if result:
                results.append(result)
                total_ticks += result['tick_count']
                total_api_calls += result['api_calls']
                total_duration += result['duration_ms']
                if result.get('rate_limited'):
                    rate_limited_count += 1
                
                rl_flag = "⚠️" if result.get('rate_limited') else "✅"
                print(f"  {rl_flag} Ticks: {result['tick_count']}, API Calls: {result['api_calls']}, Duration: {result['duration_ms']:.2f}ms")
            else:
                print(f"  ❌ Failed")
            
            # Add delay between windows to avoid rate limits
            await asyncio.sleep(2.0)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 EXPERIMENT RESULTS")
        print("=" * 60)
        print(f"Total Sampling Windows: {len(results)}/{len(sampling_windows)}")
        print(f"Total Ticks Verified: {total_ticks:,}")
        print(f"Total API Calls: {total_api_calls}")
        print(f"Total Duration: {total_duration/1000:.2f}s")
        print(f"Avg Duration per Window: {total_duration/len(results)/1000:.2f}s")
        print(f"Avg Ticks per Window: {total_ticks/len(results):.2f}")
        
        # Extrapolation
        coverage_ratio = sum((int(e) - int(s)) / 100 for s, e in sampling_windows) / (6.5 * 60 * 60)
        estimated_full_day_ticks = total_ticks / coverage_ratio
        estimated_full_day_api_calls = total_api_calls / coverage_ratio
        estimated_full_day_duration = total_duration / coverage_ratio / 1000 / 60
        
        print("\n📈 FULL DAY EXTRAPOLATION (if sampling is representative)")
        print(f"Coverage Ratio: {coverage_ratio*100:.2f}%")
        print(f"Estimated Full Day Ticks: {estimated_full_day_ticks:,.0f}")
        print(f"Estimated API Calls Needed: {estimated_full_day_api_calls:.0f}")
        print(f"Estimated Duration: {estimated_full_day_duration:.2f} minutes")
        
        # Rate Limit Analysis
        print("\n⚠️ RATE LIMIT ANALYSIS")
        print(f"Kiwoom Rate Limit: Unknown (needs testing)")
        print(f"Required TPS: {estimated_full_day_api_calls / (6.5 * 60 * 60):.2f} calls/sec")
        
        if estimated_full_day_api_calls > 1000:
            print("❌ WARNING: Full day verification may exceed reasonable API limits")
            print("✅ RECOMMENDATION: Use 5-minute sampling as proposed")
        else:
            print("✅ Full day verification is feasible within rate limits")


if __name__ == "__main__":
    asyncio.run(run_5min_sampling_experiment())
