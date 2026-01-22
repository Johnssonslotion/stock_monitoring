import json
from datetime import datetime
from collections import defaultdict

LOG_FILE = "data/raw/kiwoom/ws_raw_20260120_00.jsonl"
TARGET_START = "09:00:00"
TARGET_END = "09:05:00"

def verify_opening():
    print(f"🔍 Analyzing Kiwoom Log: {LOG_FILE}")
    print(f"⏰ Target Window: {TARGET_START} ~ {TARGET_END}")
    
    symbol_counts = defaultdict(int)
    total_lines = 0
    in_window_lines = 0
    
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            try:
                data = json.loads(line)
                # Kiwoom format: {"values": {"20": "090001", "21": "090000"...}, "type": ...}
                # Field 20 = Trade Time, Field 21 = Orderbook Time
                values = data.get("values", {})
                time_str = values.get("20", "") 
                if not time_str:
                    time_str = values.get("21", "")
                
                # Check if valid time string
                if len(time_str) == 6:
                    # Time comparison (String comparison works for HHMMSS)
                    # Window: 090000 ~ 090500
                    if "090000" <= time_str <= "090500":
                        in_window_lines += 1
                        
            except Exception as e:
                continue

    print(f"📊 Results:")
    print(f"Total Lines in File: {total_lines}")
    print(f"Lines in Window ({TARGET_START}-{TARGET_END}): {in_window_lines}")
    
    if in_window_lines > 0:
        print(f"✅ density: {in_window_lines / 300:.2f} msgs/sec")
    else:
        print("❌ No data in opening window!")

if __name__ == "__main__":
    verify_opening()
