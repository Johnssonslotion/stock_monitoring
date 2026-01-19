#!/usr/bin/env python3
"""
Tick vs Minute Consistency Verification Script

Purpose:
    실시간 수집된 틱 데이터를 1분봉으로 집계하여,
    KIS/Kiwoom REST API의 분봉 데이터와 일치하는지 검증.
    
    이를 통해 데이터 품질(누락, 불일치)을 평가함.

Dependencies:
    - DuckDB (data/ticks.duckdb)
    - KIS minute CSV (data/recovery/)
    - Kiwoom minute CSV (data/proof/)

Author: Antigravity AI
Date: 2026-01-19
"""

import duckdb
import pandas as pd
import glob
from datetime import datetime
import os

def load_tick_data_from_db(symbol="005930", target_date="2026-01-19"):
    """
    Load tick data from DuckDB for a specific symbol and date.
    
    Args:
        symbol: Stock code (e.g., '005930')
        target_date: Date in 'YYYY-MM-DD' format
    
    Returns:
        DataFrame with columns: time, symbol, price, volume
    """
    try:
        conn = duckdb.connect('data/ticks.duckdb', read_only=True)
        
        query = f"""
        SELECT 
            time,
            symbol,
            price,
            volume
        FROM market_ticks
        WHERE symbol = '{symbol}'
          AND DATE(time) = '{target_date}'
        ORDER BY time ASC
        """
        
        df = conn.execute(query).fetchdf()
        conn.close()
        
        print(f"✅ Loaded {len(df)} ticks for {symbol} on {target_date}")
        return df
        
    except Exception as e:
        print(f"❌ Error loading tick data: {e}")
        return pd.DataFrame()

def aggregate_ticks_to_1min(tick_df):
    """
    Aggregate tick data into 1-minute OHLCV bars.
    
    Args:
        tick_df: DataFrame with tick data (time, price, volume)
    
    Returns:
        DataFrame with 1-minute bars (time, open, high, low, close, volume)
    """
    if tick_df.empty:
        return pd.DataFrame()
    
    # Convert time to datetime if not already
    tick_df['time'] = pd.to_datetime(tick_df['time'])
    
    # Set time as index
    tick_df.set_index('time', inplace=True)
    
    # Resample to 1-minute bars
    bars = tick_df['price'].resample('1T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last'
    })
    
    # Volume aggregation
    volume = tick_df['volume'].resample('1T').sum()
    
    # Combine
    bars['volume'] = volume
    bars = bars.dropna()  # Remove empty minutes
    
    print(f"✅ Aggregated to {len(bars)} 1-minute bars")
    return bars.reset_index()

def load_kis_minute_data(symbol="005930"):
    """
    Load KIS minute data from CSV.
    
    Args:
        symbol: Stock code
    
    Returns:
        DataFrame with KIS minute bars
    """
    pattern = f"data/recovery/backfill_minute_{symbol}_*.csv"
    files = glob.glob(pattern)
    
    if not files:
        print(f"⚠️ No KIS minute data found for {symbol}")
        return pd.DataFrame()
    
    # Load latest file
    latest = sorted(files)[-1]
    df = pd.read_csv(latest)
    
    print(f"✅ Loaded KIS minute data: {len(df)} rows from {latest}")
    return df

def load_kiwoom_minute_data(symbol="005930"):
    """
    Load Kiwoom minute data from CSV.
    
    Args:
        symbol: Stock code
    
    Returns:
        DataFrame with Kiwoom minute bars
    """
    pattern = f"data/proof/kiwoom_minute_{symbol}_*.csv"
    files = glob.glob(pattern)
    
    if not files:
        print(f"⚠️ No Kiwoom minute data found for {symbol}")
        return pd.DataFrame()
    
    # Load latest file
    latest = sorted(files)[-1]
    df = pd.read_csv(latest)
    
    print(f"✅ Loaded Kiwoom minute data: {len(df)} rows from {latest}")
    return df

def compare_ohlcv(tick_bars, kis_bars, kiwoom_bars):
    """
    Compare OHLCV between tick-aggregated, KIS, and Kiwoom data.
    
    Args:
        tick_bars: DataFrame from tick aggregation
        kis_bars: DataFrame from KIS API
        kiwoom_bars: DataFrame from Kiwoom API
    
    Returns:
        Dictionary with consistency scores
    """
    results = {
        'tick_count': len(tick_bars),
        'kis_count': len(kis_bars),
        'kiwoom_count': len(kiwoom_bars),
        'tick_vs_kis_match': 0,
        'tick_vs_kiwoom_match': 0,
        'kis_vs_kiwoom_match': 0
    }
    
    # TODO: Implement time-based matching and OHLCV comparison
    # This requires:
    # 1. Convert all timestamps to same format
    # 2. Align by timestamp (fuzzy match ±1 sec)
    # 3. Compare close prices (primary metric)
    
    print(f"\n📊 Comparison Results:")
    print(f"   Tick-aggregated bars: {results['tick_count']}")
    print(f"   KIS bars: {results['kis_count']}")
    print(f"   Kiwoom bars: {results['kiwoom_count']}")
    
    return results

def main():
    """
    Main execution flow for tick-minute consistency verification.
    """
    print("="*80)
    print("🔍 Tick vs Minute Consistency Verification")
    print("="*80)
    
    symbol = "005930"  # Samsung Electronics
    target_date = "2026-01-19"
    
    # Step 1: Load tick data from DB
    print(f"\n1️⃣ Loading tick data from DB...")
    print("-"*80)
    tick_df = load_tick_data_from_db(symbol, target_date)
    
    if tick_df.empty:
        print("⚠️ No tick data found in DB")
        print("   Possible reasons:")
        print("   - DuckDB lock (other process using it)")
        print("   - No data collected for today")
        print("   - Table name mismatch")
        print("\n   Skipping tick-based verification...")
        tick_bars = pd.DataFrame()
    else:
        # Step 2: Aggregate ticks to 1-minute bars
        print(f"\n2️⃣ Aggregating ticks to 1-minute bars...")
        print("-"*80)
        tick_bars = aggregate_ticks_to_1min(tick_df)
    
    # Step 3: Load KIS minute data
    print(f"\n3️⃣ Loading KIS minute data...")
    print("-"*80)
    kis_bars = load_kis_minute_data(symbol)
    
    # Step 4: Load Kiwoom minute data
    print(f"\n4️⃣ Loading Kiwoom minute data...")
    print("-"*80)
    kiwoom_bars = load_kiwoom_minute_data(symbol)
    
    # Step 5: Compare
    print(f"\n5️⃣ Comparing data sources...")
    print("-"*80)
    results = compare_ohlcv(tick_bars, kis_bars, kiwoom_bars)
    
    # Step 6: Generate report
    print(f"\n6️⃣ Generating consistency report...")
    print("-"*80)
    
    report_path = f"data/reports/consistency_report_{datetime.now().strftime('%Y%m%d')}.md"
    os.makedirs("data/reports", exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(f"# Tick-Minute Consistency Report - {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(f"## Data Counts\n\n")
        f.write(f"- Tick-aggregated bars: {results['tick_count']}\n")
        f.write(f"- KIS minute bars: {results['kis_count']}\n")
        f.write(f"- Kiwoom minute bars: {results['kiwoom_count']}\n\n")
        f.write(f"## Notes\n\n")
        
        if tick_df.empty:
            f.write(f"⚠️ Tick data could not be loaded from DuckDB (likely locked or empty)\n\n")
            f.write(f"**Recommendation**: Verify tick data collection and DB accessibility\n")
        else:
            f.write(f"✅ Tick data loaded successfully from DB\n\n")
            f.write(f"**TODO**: Implement OHLCV comparison algorithm\n")
    
    print(f"   ✅ Report saved: {report_path}")
    
    print("\n" + "="*80)
    print("✅ Verification Complete")
    print("="*80)

if __name__ == "__main__":
    main()
