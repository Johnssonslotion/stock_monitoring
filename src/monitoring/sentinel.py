
import asyncio
import logging
import json
import os
import redis.asyncio as redis
import yaml
import psutil
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
        self.config = self.load_config()

    def load_config(self):
        config_path = "configs/sentinel_config.yaml"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        return {"sentinel": {}}

    async def monitor_resources(self):
        """Monitor System Resources (CPU/RAM)"""
        logger.info("🛡️ Resource Monitor Started...")
        cfg = self.config.get("sentinel", {}).get("resources", {})
        cpu_threshold = cfg.get("cpu_warning_percent", 80.0)
        mem_threshold = cfg.get("memory_warning_percent", 85.0)
        interval = cfg.get("check_interval_sec", 60)

        while self.is_running:
            await asyncio.sleep(interval)
            
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            
            if cpu > cpu_threshold:
                await self.alert(f"High CPU Usage: {cpu}%", "WARNING")
            
            if mem > mem_threshold:
                await self.alert(f"High Memory Usage: {mem}%", "WARNING")
            
            # Heartbeat Log
            logger.info(f"❤️ System Health: CPU {cpu}% | MEM {mem}%")

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
        """Doomsday Protocol: Monitor data flow and trigger failover"""
        logger.info("🛡️ Doomsday Protocol Activated: Monitoring Heartbeat...")
        
        self.last_restart_time = None
        
        while self.is_running:
            await asyncio.sleep(10) # Check every 10s
            
            now = datetime.now()
            # Market Hours Check (Simplified for now - can use same logic as Scheduler later)
            # For verification, we assume ALWAYS ACTIVE or check basic hours
            # TODO: Import TZ logic if needed. For now, strict check on data gap.
            
            for market in ["KR", "US"]: # Distinct checks
                last_time = self.last_arrival.get(market)
                if not last_time:
                    continue # Startup grace period or no data yet

                gap = (now - last_time).total_seconds()
                
                # Trigger: 60s Silence
                if gap > 60:
                    logger.error(f"💀 DEAD MAN'S SWITCH: {market} silent for {gap:.1f}s!")
                    
                    # Logic: Level 2 (Degrade) vs Level 1 (Restart)
                    # Logic: Level 2 (Degrade) vs Level 1 (Restart)
                    if self.last_restart_time and (now - self.last_restart_time).total_seconds() < 300:
                        # Level 2: Persistent Failure -> Degrade Mode
                        logger.critical("🚨 LEVEL 2 TRIGGERED: Persistent Failure -> Disabling Dual Socket")
                        if self.redis:
                            await self.redis.set("config:enable_dual_socket", "false")
                            logger.info("💾 Config Saved: config:enable_dual_socket = false")
                            await self.alert(f"Failed to recover {market}. Switching to SINGLE SOCKET mode.", "CRITICAL")
                    else:
                        # Circuit Breaker Check
                        if await self.check_circuit_breaker():
                            # Level 1: First Failure -> Just Restart
                            logger.warning("🔨 LEVEL 1 TRIGGERED: Attempting Hard Restart")
                            await self.alert(f"{market} data stopped. Sending Suicide Packet.", "WARNING")

                            # ACTION: Suicide Packet
                            if self.redis:
                                await self.redis.publish("system:control", json.dumps({"command": "restart", "reason": f"no_data_{market}"}))
                                self.last_restart_time = now
                                self._record_restart()
                        else:
                            logger.critical("🛑 CIRCUIT BREAKER TRIPPED: Too many restarts! Manual intervention required.")
                            await self.alert(f"CIRCUIT BREAKER: {market} dead, but max restarts exceeded. System HALTED.", "CRITICAL")
                        
                    # Wait for restart to happen (prevent spamming)
                    await asyncio.sleep(60) 

    def _record_restart(self):
        """Record restart timestamp"""
        if not hasattr(self, 'restart_history'):
            self.restart_history = []
        self.restart_history.append(datetime.now())
        
        # Cleanup old history (> 1 hour)
        limit = self.config.get("circuit_breaker", {}).get("cool_down_minutes", 60)
        cutoff = datetime.now() - timedelta(minutes=limit)
        self.restart_history = [t for t in self.restart_history if t > cutoff]
        
    async def check_circuit_breaker(self) -> bool:
        """Return True if safe to restart, False if tripped"""
        if not hasattr(self, 'restart_history'):
            self.restart_history = []
            
        limit_count = self.config.get("sentinel", {}).get("circuit_breaker", {}).get("max_restarts_per_hour", 3)
        current_count = len(self.restart_history)
        
        if current_count >= limit_count:
            logger.error(f"Circuit Breaker: {current_count}/{limit_count} restarts in last hour.")
            return False
            
        return True 
            
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
        # 패턴 구독: ticker.kr, ticker.us 모두 수신
        await pubsub.psubscribe("ticker.*")
        await pubsub.subscribe("market_orderbook")  # orderbook은 직접 구독 유지
        
        logger.info("Sentinel started. Monitoring 'ticker.*' pattern and 'market_orderbook'...")
        
        # Start heartbeat monitor
        asyncio.create_task(self.monitor_heartbeat())
        
        # Start resource monitor
        asyncio.create_task(self.monitor_resources())
        
        async for message in pubsub.listen():
            msg_type = message['type']
            
            if msg_type == 'pmessage':  # 패턴 구독 메시지 (ticker.*)
                try:
                    channel = message['channel']  # ticker.kr 또는 ticker.us
                    raw_data = message['data']
                    
                    # ticker.* 채널은 모두 MarketData 포맷
                    data = MarketData.model_validate_json(raw_data)
                    await self.process_ticker(data)
                    
                except Exception as e:
                    logger.error(f"Error processing pattern message {channel} in Sentinel: {e}")
                    
            elif msg_type == 'message':  # 직접 구독 메시지
                try:
                    channel = message['channel']
                    raw_data = message['data']
                    
                    if channel == "market_orderbook":
                        data = json.loads(raw_data)
                        await self.process_orderbook(data)
                        
                except Exception as e:
                    logger.error(f"Error processing {channel} in Sentinel: {e}")

if __name__ == "__main__":
    sentinel = Sentinel()
    asyncio.run(sentinel.run())
