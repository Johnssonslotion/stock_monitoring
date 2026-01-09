
import redis
import json
import time
import random
from datetime import datetime

import os

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def simulate():
    try:
        r = redis.from_url(REDIS_URL)
        print("Simulator Started. Publishing to 'market_ticker' and 'news_alert'...")
        
        symbols = ['005930', 'TSLA'] # Matches UI Hardcoding for now
        prices = {'005930': 78500, 'TSLA': 245.5}
        
        count = 0
        while True:
            # 1. Update Tickers
            for symbol in symbols:
                # Random drift
                prices[symbol] += random.uniform(-10, 10) if symbol == '005930' else random.uniform(-0.5, 0.5)
                
                ticker = {
                    "type": "ticker",
                    "symbol": symbol,
                    "price": round(prices[symbol], 2),
                    "change": round(random.uniform(-1, 1), 2),
                    "volume": 1000 + random.randint(0, 500),
                    "timestamp": datetime.now().isoformat()
                }
                r.publish("market_ticker", json.dumps(ticker))
            
            # 2. Occasional Alert
            if count % 10 == 0:
                alert = {
                    "type": "alert",
                    "symbol": "TSLA",
                    "headline": f"Tesla Q4 Delivery Beat Simulation #{count//10}",
                    "url": "https://www.tesla.com",
                    "source": "Simulator",
                    "keywords": ["Tesla", "Growth"]
                }
                r.publish("news_alert", json.dumps(alert))
                print(f"Published Alert: {alert['headline']}")
            
            count += 1
            time.sleep(2) # Every 2 seconds
            
    except KeyboardInterrupt:
        print("Stopped.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    simulate()
