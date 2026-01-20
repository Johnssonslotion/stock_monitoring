"""
Daily Data Quality Verification Script
Option B: Volume + OHLCV Consistency

Safe for worktree - runs independently without affecting containers.
"""

import asyncio
import aiohttp
import os
import sys
from datetime import datetime, date
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, '/home/ubuntu/workspace/stock_backtest')

load_dotenv(".env.backtest")

# Config
KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")


async def get_kis_token():
    """Get KIS Access Token"""
    url = f"{KIS_BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json; utf-8"}
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("access_token")
            return None


async def get_kis_minute_candles(symbol, date_str, token):
    """
    Get KIS 1-minute candles for a symbol
    TR: FHKST03010200 (국내주식 기간별 시세)
    """
    url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST03010200",
        "custtype": "P"
    }
    
    # Date format: YYYYMMDD
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_DATE_1": date_str,  # Start date
        "FID_INPUT_DATE_2": date_str,  # End date (same = 1 day)
        "FID_PERIOD_DIV_CODE": "M",    # M = Minute
        "FID_ORG_ADJ_PRC": "0"         # 0 = Original price
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                candles = data.get('output2', [])
                return candles
            else:
                error = await resp.text()
                print(f"❌ KIS API Error: {error[:200]}")
                return []


async def get_db_tick_aggregation(symbol, target_date):
    """Get tick aggregation from DuckDB (worktree-safe read-only)"""
    try:
        import duckdb
        
        conn = duckdb.connect('data/ticks.duckdb', read_only=True)
        
        # Aggregate ticks into 1-minute candles
        query = f"""
        SELECT 
            DATE_TRUNC('minute', timestamp) as minute,
            MIN(price) as low,
            MAX(price) as high,
            FIRST(price ORDER BY timestamp) as open,
            LAST(price ORDER BY timestamp) as close,
            SUM(volume) as volume,
            COUNT(*) as tick_count
        FROM ticks
        WHERE symbol = '{symbol}'
          AND DATE(timestamp) = '{target_date}'
        GROUP BY DATE_TRUNC('minute', timestamp)
        ORDER BY minute
        """
        
        result = conn.execute(query).fetchall()
        conn.close()
        
        return result
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return []


async def verify_symbol_quality(symbol, date_str):
    """
    Verify data quality for a symbol
    
    Returns:
        dict: {
            'symbol': str,
            'volume_match': bool,
            'ohlcv_consistency': float,
            'details': str
        }
    """
    print(f"\n{'='*60}")
    print(f"🔍 Verifying: {symbol} on {date_str}")
    print(f"{'='*60}")
    
    # 1. Get KIS minute candles
    token = await get_kis_token()
    if not token:
        return {'symbol': symbol, 'error': 'Token failed'}
    
    kis_candles = await get_kis_minute_candles(symbol, date_str, token)
    
    if not kis_candles:
        print(f"⚠️ No KIS candles (symbol not traded today or API issue)")
        return {'symbol': symbol, 'error': 'No KIS data'}
    
    print(f"✅ KIS: {len(kis_candles)} minute candles")
    
    # 2. Get DB tick aggregation
    db_candles = await get_db_tick_aggregation(symbol, date_str)
    
    if not db_candles:
        print(f"❌ No DB data")
        return {'symbol': symbol, 'error': 'No DB data'}
    
    print(f"✅ DB: {len(db_candles)} minute candles")
    
    # 3. Compare Volume
    kis_total_volume = sum(int(c.get('acml_vol', 0) or 0) for c in kis_candles)
    db_total_volume = sum(row[5] for row in db_candles)  # volume column
    
    volume_error = abs(kis_total_volume - db_total_volume) / kis_total_volume if kis_total_volume > 0 else 0
    
    print(f"\n📊 Volume Comparison:")
    print(f"  KIS Total: {kis_total_volume:,}")
    print(f"  DB Total:  {db_total_volume:,}")
    print(f"  Error:     {volume_error*100:.3f}%")
    
    volume_pass = volume_error < 0.001  # 0.1% threshold
    
    # 4. OHLCV Consistency (sample check)
    # Match by time and compare OHLCV
    consistency_checks = 0
    consistency_pass = 0
    
    # Create DB candle dict by minute
    db_dict = {}
    for row in db_candles:
        minute_str = row[0].strftime("%H%M") if hasattr(row[0], 'strftime') else str(row[0])
        db_dict[minute_str] = {
            'low': row[1],
            'high': row[2],
            'open': row[3],
            'close': row[4],
            'volume': row[5]
        }
    
    print(f"\n🔬 OHLCV Consistency Check (sample):")
    for kis_c in kis_candles[:10]:  # Check first 10 candles
        time_str = kis_c.get('stck_bsop_date', '')[-4:]  # HHMM
        
        if time_str in db_dict:
            db_c = db_dict[time_str]
            consistency_checks += 1
            
            # Compare OHLC (allow 0.5% tolerance)
            kis_high = float(kis_c.get('stck_hgpr', 0))
            kis_low = float(kis_c.get('stck_lwpr', 0))
            
            if kis_high > 0 and kis_low > 0:
                high_match = abs(db_c['high'] - kis_high) / kis_high < 0.005
                low_match = abs(db_c['low'] - kis_low) / kis_low < 0.005
                
                if high_match and low_match:
                    consistency_pass += 1
                    print(f"  ✅ {time_str}: High/Low match")
                else:
                    print(f"  ❌ {time_str}: KIS H/L={kis_high}/{kis_low}, DB H/L={db_c['high']}/{db_c['low']}")
    
    consistency_rate = consistency_pass / consistency_checks if consistency_checks > 0 else 0
    
    print(f"\n📈 Consistency: {consistency_pass}/{consistency_checks} = {consistency_rate*100:.1f}%")
    
    # Final verdict
    print(f"\n{'='*60}")
    if volume_pass and consistency_rate > 0.95:
        print(f"✅ PASS: Data quality verified")
    else:
        print(f"⚠️ WARNING: Quality issues detected")
    
    return {
        'symbol': symbol,
        'volume_error': volume_error,
        'volume_pass': volume_pass,
        'consistency_rate': consistency_rate,
        'kis_candles': len(kis_candles),
        'db_candles': len(db_candles)
    }


async def main():
    """Verify today's data quality"""
    today = date.today().strftime("%Y%m%d")
    
    print(f"\n🧪 Daily Data Quality Verification")
    print(f"Date: {today}")
    print(f"Strategy: Volume + OHLCV Consistency (Option B)")
    print(f"⚠️ Worktree Mode: Read-only DB access")
    
    # Test with sample symbols
    test_symbols = ["005930", "373220", "091180"]  # Samsung, LG Energy, Foosung
    
    results = []
    for symbol in test_symbols:
        result = await verify_symbol_quality(symbol, today)
        results.append(result)
        await asyncio.sleep(1)  # Rate limit protection
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 VERIFICATION SUMMARY")
    print(f"{'='*60}")
    
    for r in results:
        if 'error' in r:
            print(f"{r['symbol']}: ❌ {r['error']}")
        else:
            status = "✅ PASS" if r['volume_pass'] and r['consistency_rate'] > 0.95 else "⚠️ WARN"
            print(f"{r['symbol']}: {status} (Vol: {r['volume_error']*100:.2f}%, OHLCV: {r['consistency_rate']*100:.0f}%)")


if __name__ == "__main__":
    asyncio.run(main())
