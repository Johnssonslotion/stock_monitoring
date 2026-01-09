import yfinance as yf
import pandas as pd
import asyncpg
import asyncio
import os
from datetime import datetime, timedelta

# Config
DB_URL = os.getenv("TIMESCALEDB_URL", "postgresql://postgres:password@stock-timescale:5432/stockval")
SYMBOLS = ['005930.KS', '000660.KS', '122630.KS', '252670.KS', '069500.KS']

async def backfill():
    conn = await asyncpg.connect(DB_URL)
    print(f"Connected to DB. Processing {len(SYMBOLS)} symbols...")
    
    for sym in SYMBOLS:
        print(f"Fetching 1m history for {sym}...")
        try:
            # yfinance 1m data is available for last 7 days
            df = yf.download(sym, period="5d", interval="1m", progress=False)
            if df.empty:
                print(f"No data for {sym}")
                continue
            
            # Filter for Jan 6 and Jan 7
            df = df[(df.index >= '2026-01-06') & (df.index < '2026-01-08')]
            if df.empty:
                print(f"No Jan 6-7 data for {sym}")
                continue
                
            records = []
            for ts, row in df.iterrows():
                # We save to market_candles to match the loader.py structure
                # Or we can insert into market_ticks to make it visible in the Pro Terminal (Continuous Aggregates)
                # Let's insert into market_ticks as a "synthetic tick" at the close of each minute
                records.append((
                    ts.to_pydatetime(), 
                    sym.split('.')[0], # Strip .KS
                    float(row['Close']),
                    float(row['Volume']),
                    0.0 # change
                ))
            
            # Bulk insert into market_ticks
            await conn.copy_records_to_table(
                'market_ticks',
                records=records,
                columns=['time', 'symbol', 'price', 'volume', 'change']
            )
            print(f"Successfully backfilled {len(records)} ticks for {sym}")
            
        except Exception as e:
            print(f"Error backfilling {sym}: {e}")
            
    await conn.close()
    print("Backfill complete.")

if __name__ == "__main__":
    asyncio.run(backfill())
