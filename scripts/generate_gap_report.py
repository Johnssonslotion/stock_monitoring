import pandas as pd
import glob
import os
from datetime import datetime, timedelta

def generate_expected_times():
    """Generate expected minute strings HHMM00 for 09:00 to 15:30"""
    times = []
    current = datetime.strptime("090000", "%H%M%S")
    end = datetime.strptime("153000", "%H%M%S")
    
    while current <= end:
        times.append(current.strftime("%H%M%S"))
        current += timedelta(minutes=1)
    return set(times)

def analyze_gaps():
    print("# Data Gap Report (Minute Basis) - 2026-01-19\n")
    print("| Symbol | Recovered | Expected | Coverage (%) | Missing Examples |")
    print("|---|---|---|---|---|")
    
    files = glob.glob("data/recovery/backfill_minute_*.csv")
    files.sort()
    
    if not files:
        print("\nNo recovery files found.")
        return

    expected_set = generate_expected_times()
    total_expected = len(expected_set) # 391 minutes (6.5 hours + 1 min inclusive? usually 381 mins? 9:00 to 15:20 regular + 15:30 closing?)
    # KIS Minute usually: 090000..152000 (381 mins) + 153000 (1 min) = 382?
    # Let's assume standard minutes.
    
    # Actually, let's just use the range 09:00 to 15:30 inclusive as strict expected.
    # Standard KIS output times might vary (e.g. 090100 is first bar?). 
    # Let's assume 381 bars normally (09:01 ~ 15:20) + 15:30.
    
    for f in files:
        # File format: backfill_minute_CODE_DATE.csv
        try:
            filename = os.path.basename(f)
            symbol = filename.split('_')[2]
            
            df = pd.read_csv(f)
            
            # Timestamp column: stck_cntg_hour
            # Ensure strictly string
            df['stck_cntg_hour'] = df['stck_cntg_hour'].astype(str).str.zfill(6)
            
            recovered_times = set(df['stck_cntg_hour'])
            
            # Missing
            missing = sorted(list(expected_set - recovered_times))
            count = len(recovered_times)
            coverage = (count / total_expected) * 100
            
            # Format missing examples (first 3)
            missing_str = ", ".join(missing[:3]) + ("..." if len(missing) > 3 else "") if missing else "None"
            
            # Filter huge missing lists for cleaner output
            if coverage > 90:
                pass
            
            print(f"| `{symbol}` | {count} | {total_expected} | **{coverage:.1f}%** | {missing_str} |")
            
        except Exception as e:
            print(f"Error analyzing {f}: {e}")

if __name__ == "__main__":
    analyze_gaps()
