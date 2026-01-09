import os
import logging
import yfinance as yf
import pandas as pd
import asyncpg
import asyncio
from datetime import datetime, timedelta
import yaml

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("USLoader")

# Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

CONFIG_PATH = "configs/market_symbols.yaml"

async def save_to_timescale(df: pd.DataFrame, symbol: str, interval: str):
    """Save DataFrame to TimescaleDB market_candles table"""
    if df.empty:
        return

    conn = await asyncpg.connect(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT
    )
    
    try:
        # Prepare records: [time, symbol, interval, open, high, low, close, volume]
        records = []
        for ts, row in df.iterrows():
            records.append((
                ts.to_pydatetime(),
                symbol,
                interval,
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                float(row['Volume'])
            ))
        
        await conn.copy_records_to_table(
            'market_candles',
            records=records,
            columns=['time', 'symbol', 'interval', 'open', 'high', 'low', 'close', 'volume']
        )
        logger.info(f"Saved {len(records)} candles for {symbol} ({interval})")
    except Exception as e:
        logger.error(f"Failed to save {symbol} to DB: {e}")
    finally:
        await conn.close()

async def load_us_history():
    """Load US market history data using yfinance"""
    # 1. Load symbols from config
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    us_symbols = []
    # Collect all US symbols from indices, leverage, sectors
    us_data = config.get('market_data', {}).get('us', {})
    
    for category in ['indices', 'leverage']:
        for item in us_data.get(category, []):
            us_symbols.append(item['symbol'])
            
    for sector in us_data.get('sectors', {}).values():
        if 'etf' in sector:
            us_symbols.append(sector['etf']['symbol'])
        # Also possibly top3 but sticking to ETFs for now as requested
            
    us_symbols = list(set(us_symbols))
    logger.info(f"Loading history for {len(us_symbols)} US symbols: {us_symbols}")

    for symbol in us_symbols:
        try:
            logger.info(f"Fetching 1m data for {symbol}...")
            # yfinance 1m data is limit to last 7 days
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="5d", interval="1m")
            
            if not df.empty:
                await save_to_timescale(df, symbol, "1m")
            else:
                logger.warning(f"No data found for {symbol}")
                
        except Exception as e:
            logger.error(f"Error loading {symbol}: {e}")

if __name__ == "__main__":
    asyncio.run(load_us_history())
