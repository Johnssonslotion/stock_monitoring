import yfinance as yf
import pandas as pd

def test_yf(symbol):
    print(f"Testing {symbol}...")
    try:
        # 1m data, max period (usually 7 days)
        print("  [Request] 1m interval, period=7d")
        df = yf.download(symbol, interval="1m", period="7d", progress=False)
        print(f"  - 1m Count: {len(df)}")
        if not df.empty:
            print(f"  - Range: {df.index.min()} ~ {df.index.max()}")
            
        # 60m data, max period (usually 730 days for 1h)
        print("  [Request] 60m interval, period=730d")
        df60 = yf.download(symbol, interval="60m", period="730d", progress=False)
        print(f"  - 60m Count: {len(df60)}")
        if not df60.empty:
            print(f"  - Range: {df60.index.min()} ~ {df60.index.max()}")
            
    except Exception as e:
        print(f"  - Error: {e}")

if __name__ == "__main__":
    test_yf("AAPL")      # US
    test_yf("005930.KS") # KR
