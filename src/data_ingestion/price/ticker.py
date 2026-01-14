import asyncio
import os
import random
import logging
import redis.asyncio as redis
import json
import yaml
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticker")

# Env vars
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APP_ENV = os.getenv("APP_ENV", "dev")

async def load_symbols():
    try:
        with open("configs/kr_symbols.yaml", "r") as f:
            config = yaml.safe_load(f)
            symbols = []
            if "symbols" in config:
                if "indices" in config["symbols"]:
                    symbols.extend([s["symbol"] for s in config["symbols"]["indices"]])
                if "leverage" in config["symbols"]:
                     symbols.extend([s["symbol"] for s in config["symbols"]["leverage"]])
                if "sectors" in config["symbols"]:
                    for sector in config["symbols"]["sectors"].values():
                         if "top3" in sector:
                             symbols.extend([s["symbol"] for s in sector["top3"]])
            return symbols
    except Exception as e:
        logger.error(f"Failed to load symbols: {e}")
        return ["005930.KS", "000660.KS"] # Fallback

async def mock_ticker_gen():
    """Generates random mock ticks for testing"""
    r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    symbols = await load_symbols()
    logger.info(f"🚀 Starting Mock Ticker for {len(symbols)} symbols")

    while True:
        try:
            for symbol in symbols:
                # Random price movement
                price = 70000 + random.uniform(-1000, 1000)
                msg = {
                    "type": "TICK",
                    "symbol": symbol,
                    "price": round(price, 0),
                    "volume": random.randint(1, 100),
                    "time": datetime.now().isoformat(),
                    "market": "kr"
                }
                
                # Publish to Redis
                await r.publish("market_ticker", json.dumps(msg))
                
            await asyncio.sleep(1) # 1 sec interval
        except Exception as e:
            logger.error(f"Ticker Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(mock_ticker_gen())
