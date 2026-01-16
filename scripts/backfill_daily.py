import json
import os
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime
from pathlib import Path

# 설정
TARGET_FILE = 'scripts/target_stocks.json'
OUTPUT_DIR = 'scripts/data_ingest'
START_DATE = '2024-01-01'  # 1년치 데이터

def load_targets():
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def ensure_dir(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)

def fetch_daily_data():
    targets = load_targets()
    ensure_dir(OUTPUT_DIR)
    
    print(f"🚀 Starting daily data backfill for {len(targets)} symbols...")
    print(f"📅 Range: {START_DATE} ~ Today")
    
    for item in targets:
        code = item['code']
        name = item['name_kr']
        
        try:
            # Fetch Data (Daily)
            df = fdr.DataReader(code, START_DATE)
            
            if df.empty:
                print(f"⚠️  No data for {name} ({code})")
                continue
                
            # Format columns for our schema
            # KIS/FinanceDataReader columns: Open, High, Low, Close, Volume, Change
            # Our CSV Schema: time, symbol, interval, open, high, low, close, volume (Change는 계산 가능하므로 일단 제외 or 별도 처리)
            
            df.reset_index(inplace=True)
            df['symbol'] = code
            df['interval'] = '1d'
            df.rename(columns={
                'Date': 'time',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)
            
            # Select & Order columns
            out_df = df[['time', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']]
            
            # Save to CSV
            filename = f"{OUTPUT_DIR}/{code}_daily_candles.csv"
            out_df.to_csv(filename, index=False)
            print(f"✅ Saved {name} ({code}): {len(out_df)} rows -> {filename}")
            
        except Exception as e:
            print(f"❌ Error fetching {name} ({code}): {e}")

    print("\n🎉 All done! You can now run 'python scripts/ingest_csv.py' to load this data.")

if __name__ == "__main__":
    # Ensure finance-datareader is installed
    try:
        import FinanceDataReader
    except ImportError:
        print("📦 Installing FinanceDataReader...")
        os.system("pip install finance-datareader")
        
    fetch_daily_data()
