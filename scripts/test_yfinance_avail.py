
import yfinance as yf
from datetime import datetime
import pandas as pd

def check_yfinance():
    symbol = "AAPL"
    print(f"Fetching {symbol} via yfinance...")
    
    # Try fetching last 5 days interval 1m
    # Jan 13 is target.
    data = yf.download(symbol, interval="1m", period="5d")
    
    print("Columns:", data.columns)
    print("Last 5 rows:")
    print(data.tail())
    
    # Check if Jan 13 exists
    # Convert index to UTC if tz-aware, else assume local (US Eastern)
    # yfinance 1m usually returns US/Eastern localized but pandas converts.
    
    # Check explicitly for 2026-01-13
    day_str = "2026-01-13"
    try:
        subset = data.loc[day_str]
        print(f"\nData for {day_str}: {len(subset)} rows")
    except KeyError:
        print(f"\nNo data found for {day_str} via index loc")
        
    # Print max index
    print(f"\nMax Index: {data.index.max()}")
    
if __name__ == "__main__":
    check_yfinance()
