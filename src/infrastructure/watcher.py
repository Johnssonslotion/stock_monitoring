import asyncio
import logging
import os
import shutil
import json
import redis.asyncio as redis
from datetime import datetime

logger = logging.getLogger("SystemWatcher")
logging.basicConfig(level=logging.INFO)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHECK_INTERVAL = 10  # Seconds
DOOMSDAY_TIMEOUT = 60  # Seconds (Rule #3)
DISK_THRESHOLD = 80.0  # Percentage

class SystemWatcher:
    def __init__(self):
        self.redis = None
        self.last_tick_time = datetime.now()
        self.tick_count = 0
        self.running = False
        
    async def start(self):
        self.running = True
        self.redis = await redis.from_url(REDIS_URL, decode_responses=True)
        logger.info("🛡️ System Watcher Started")
        
        # Start Listeners
        asyncio.create_task(self._monitor_ticks())
        asyncio.create_task(self._monitor_resources())
        
        # Wait for stop
        while self.running:
            await asyncio.sleep(1)
            
    async def _monitor_ticks(self):
        """Monitor Redis Channel for activity"""
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("tick:*")
        
        async for msg in pubsub.listen():
            if msg['type'] == 'pmessage':
                self.tick_count += 1
                self.last_tick_time = datetime.now()
                
    async def _monitor_resources(self):
        """Periodic Health Check"""
        while self.running:
            now = datetime.now()
            
            # 1. Doomsday Check (Rule #3)
            silence_duration = (now - self.last_tick_time).total_seconds()
            
            if silence_duration > DOOMSDAY_TIMEOUT:
                logger.critical(f"💀 DOOMSDAY DETECTED: No ticks for {silence_duration:.1f}s")
                await self._trigger_restart("Doomsday Protocol: Zero Data")
                # Reset timer to prevent flooding
                self.last_tick_time = now 
            
            # 2. Disk Check
            total, used, free = shutil.disk_usage("/")
            percent = (used / total) * 100
            
            if percent > DISK_THRESHOLD:
                logger.warning(f"💾 DISK FULL WARNING: {percent:.1f}% used")
                await self._publish_alert("WARNING", f"Disk Usage High: {percent:.1f}%")
                # TODO: Trigger Satellite Eviction
                
            # Log Stat
            if self.tick_count > 0:
                logger.info(f"❤️ System Alive: {self.tick_count} ticks in last window")
                self.tick_count = 0
                
            await asyncio.sleep(CHECK_INTERVAL)

    async def _trigger_restart(self, reason: str):
        """Publish Suicide Packet"""
        payload = {
            "command": "restart",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        await self.redis.publish("system:control", json.dumps(payload))
        await self._publish_alert("CRITICAL", f"Triggering Restart: {reason}")
        
    async def _publish_alert(self, level: str, msg: str):
        payload = {
            "level": level,
            "message": msg,
            "timestamp": datetime.now().isoformat()
        }
        await self.redis.publish("system:alerts", json.dumps(payload))

if __name__ == "__main__":
    watcher = SystemWatcher()
    asyncio.run(watcher.start())
