#!/usr/bin/env python3
"""
Convert minute-level CSV data from data/ folder to ingestion-ready format.

Input Format (data/005930_삼성전자.csv):
    Date,Time,Open,High,Low,Close,Volume
    20260114,1530,140300,140300,140300,140300,1981323

Output Format (scripts/data_ingest/005930_candles.csv):
    time,symbol,interval,open,high,low,close,volume
    2026-01-14 15:30:00,005930,1m,140300,140300,140300,140300,1981323
"""

import csv
import os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
OUTPUT_DIR = Path("scripts/data_ingest")

def parse_datetime(date_str: str, time_str: str) -> str:
    """
    Convert Korean date/time format to ISO timestamp.
    
    Args:
        date_str: YYYYMMDD format (e.g., '20260114')
        time_str: HHMM or HHM format (e.g., '1530', '945')
    
    Returns:
        ISO timestamp string (e.g., '2026-01-14 15:30:00')
    """
    # Parse date
    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    
    # Parse time (handle both HMM and HHMM)
    time_str = time_str.zfill(4)  # Pad to 4 digits
    hour = int(time_str[:2])
    minute = int(time_str[2:4])
    
    dt = datetime(year, month, day, hour, minute)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def extract_symbol(filename: str) -> str:
    """
    Extract symbol code from filename.
    
    Example: '005930_삼성전자.csv' -> '005930'
    """
    return filename.split('_')[0]

def convert_csv(input_path: Path, output_path: Path, symbol: str):
    """
    Convert CSV from Korean format to TimescaleDB ingestion format.
    """
    print(f"🔄 Converting {input_path.name}...")
    
    converted_rows = []
    with open(input_path, 'r', encoding='utf-8-sig') as f:  # Handle BOM
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                time = parse_datetime(row['Date'], row['Time'])
                converted_rows.append({
                    'time': time,
                    'symbol': symbol,
                    'interval': '1m',
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': row['Volume']
                })
            except Exception as e:
                print(f"⚠️  Skipping row due to error: {e}")
                continue
    
    # Write output
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        if converted_rows:
            fieldnames = ['time', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(converted_rows)
    
    print(f"✅ Converted {len(converted_rows):,} rows -> {output_path}")
    return len(converted_rows)

def main():
    """Process all CSV files in data/ directory."""
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("📦 Minute Data Conversion - data/ → scripts/data_ingest/")
    print("=" * 60)
    
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    print(f"\nFound {len(csv_files)} CSV files in data/\n")
    
    total_rows = 0
    for csv_file in csv_files:
        symbol = extract_symbol(csv_file.name)
        output_file = OUTPUT_DIR / f"{symbol}_candles.csv"
        
        rows = convert_csv(csv_file, output_file, symbol)
        total_rows += rows
        print()
    
    print("=" * 60)
    print(f"🎉 Conversion Complete!")
    print(f"   Total files: {len(csv_files)}")
    print(f"   Total rows: {total_rows:,}")
    print(f"   Output: {OUTPUT_DIR}/")
    print("=" * 60)
    print("\n▶ Next step: python scripts/ingest_csv.py")

if __name__ == "__main__":
    main()
