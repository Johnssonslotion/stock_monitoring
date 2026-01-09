
import asyncio
import logging
import json
import os
import redis.asyncio as redis
from datetime import datetime, timedelta
from src.core.schema import MarketData

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Sentinel")

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HEARTBEAT_THRESHOLD_SEC = 300  # 5 minutes
PRICE_CHANGE_THRESHOLD = 0.10  # 10%

class Sentinel:
    def __init__(self):
        self.redis = None
        self.last_prices = {}  # {symbol: price}
        self.last_arrival = {} # {market: timestamp}
        self.is_running = True

    async def alert(self, msg: str, level: str = "WARNING"):
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": msg
        }
        logger.warning(f"🚨 ALERT [{level}]: {msg}")
        if self.redis:
            await self.redis.publish("system_alerts", json.dumps(alert_data))

    async def monitor_heartbeat(self):
        """Monitor if data is flowing for each market"""
        while self.is_running:
            await asyncio.sleep(60)
            now = datetime.now()
            # Simple check for now: assuming we have KR and US symbols
            # In production, we'd check based on market hours
            for market, last_time in self.last_arrival.items():
                if (now - last_time).total_seconds() > HEARTBEAT_THRESHOLD_SEC:
                    await self.alert(f"Data flow for {market} has stopped for over 5 minutes!", "CRITICAL")
            
    async def process_ticker(self, data: MarketData):
        symbol = data.symbol
        price = data.price
        
        # 1. Market Heartbeat Update
        # Guess market: US symbols have prefix NYS/NAS, KR are 6 digits
        market = "US" if any(p in symbol for p in ["NYS", "NAS", "AMS"]) else "KR"
        self.last_arrival[market] = datetime.now()

        # 2. Check for Invalid Data (e.g. Volume <= 0)
        if data.volume < 0:
            await self.alert(f"Invalid volume detected for {symbol}: {data.volume}")

        # 3. Check for Price Anomaly (>10% Jump)
        if symbol in self.last_prices:
            prev_price = self.last_prices[symbol]
            if prev_price > 0:
                change = abs(price - prev_price) / prev_price
                if change > PRICE_CHANGE_THRESHOLD:
                    await self.alert(
                        f"Price anomaly for {symbol}: {prev_price} -> {price} ({change*100:.2f}%)", 
                        "HIGH"
                    )
        
        self.last_prices[symbol] = price

    async def process_orderbook(self, data: dict):
        """Monitor orderbook flow"""
        symbol = data.get('symbol', 'UNKNOWN')
        market = "US" if any(p in symbol for p in ["NYS", "NAS", "AMS"]) else "KR"
        self.last_arrival[f"{market}_ORDERBOOK"] = datetime.now()

    async def run(self):
        self.redis = await redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("market_ticker", "market_orderbook")
        
        logger.info("Sentinel started. Monitoring 'market_ticker' and 'market_orderbook'...")
        
        # Start heartbeat monitor
        asyncio.create_task(self.monitor_heartbeat())
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    channel = message['channel']
                    raw_data = message['data']
                    
                    if channel == "market_ticker":
                        data = MarketData.model_validate_json(raw_data)
                        await self.process_ticker(data)
                    elif channel == "market_orderbook":
                        data = json.loads(raw_data)
                        await self.process_orderbook(data)
                        
                except Exception as e:
                    logger.error(f"Error processing {channel} in Sentinel: {e}")

if __name__ == "__main__":
    sentinel = Sentinel()
    asyncio.run(sentinel.run())
