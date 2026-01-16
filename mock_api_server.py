"""
Simple Mock API Server for Testing Frontend Data Integration
Serves candle data from local CSV files on Port 8002
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import glob
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load CSV data
CANDLE_DATA = {}

def load_csv_data():
    """Load all candle CSV files into memory"""
    csv_files = glob.glob("scripts/data_ingest/*_candles.csv")
    for file in csv_files:
        symbol = file.split("/")[-1].split("_")[0]
        try:
            df = pd.read_csv(file, names=["time", "symbol", "interval", "open", "high", "low", "close", "volume"])
            CANDLE_DATA[symbol] = df
            print(f"✅ Loaded {len(df)} candles for {symbol}")
        except Exception as e:
            print(f"❌ Failed to load {file}: {e}")

@app.on_event("startup")
async def startup():
    load_csv_data()
    print(f"📦 Loaded data for {len(CANDLE_DATA)} symbols")

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "db": {"connected": True, "response_ms": 1}, "redis": {"connected": True, "response_ms": 1}, "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/candles/{symbol}")
async def get_candles(symbol: str, limit: int = 5000, interval: str = "1d", x_api_key: str = Header(None)):
    if x_api_key != "backtest-secret-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if symbol not in CANDLE_DATA:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    df = CANDLE_DATA[symbol]
    
    # Filter by interval if needed (all data is 1m in CSV, so we'll just return it)
    data = df.tail(limit).to_dict('records')
    
    # Convert to API format
    result = []
    for row in data:
        result.append({
            "time": row["time"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["volume"])
        })
    
    return result

@app.get("/api/v1/market-map/{market}")
async def get_market_map(market: str, x_api_key: str = Header(None)):
    if x_api_key != "backtest-secret-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    symbols = []
    for symbol, df in CANDLE_DATA.items():
        if len(df) > 0:
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            symbols.append({
                "symbol": symbol,
                "name": f"Stock {symbol}",
                "marketCap": float(latest["close"]) * 1000000,
                "price": float(latest["close"]),
                "prevPrice": float(prev["close"]),
                "change": round(((float(latest["close"]) - float(prev["close"])) / float(prev["close"]) * 100), 2),
                "isActive": True,
                "currency": "KRW",
                "category": "STOCK"
            })
    
    return {"symbols": symbols, "timestamp": datetime.now().isoformat(), "market": "kr", "currency": "KRW"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
