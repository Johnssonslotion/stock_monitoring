"""
Dual WebSocket Manager Module
- Separates Realtime Ticks (Execution) and Orderbooks (Hoga) into two distinct WebSocket connections.
- Prevents Head-of-Line Blocking and Protocol Errors (invalid tr_key mixed usage).
"""
import asyncio
import logging
import json
import websockets
import redis.asyncio as redis
from typing import Optional, List, Dict
from src.data_ingestion.price.common.websocket_base import BaseCollector
from src.data_ingestion.logger.raw_logger import RawWebSocketLogger

logger = logging.getLogger(__name__)

class DualWebSocketManager:
    """
    Manages two separate WebSocket connections:
    1. Tick Socket: For Trade/Execution data (H0STCNT0, HDFSCNT0) -> Low Latency critical
    2. Orderbook Socket: For Hoga data (H0STASP0, HDFSASP0) -> High Throughput
    """
    def __init__(self, collectors: List[BaseCollector], redis_url: str):
        self.collectors: Dict[str, BaseCollector] = {c.tr_id: c for c in collectors}
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        
        # Connection State
        self.ws_tick: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_orderbook: Optional[websockets.WebSocketClientProtocol] = None
        
        self.lock_tick = asyncio.Lock()
        self.lock_orderbook = asyncio.Lock()
        
        self.approval_key = None
        self.active_markets = set()
        
        # Raw Logger (Shared)
        self.raw_logger = RawWebSocketLogger(retention_hours=120)  # 5일 보존
        
        # Current URLs (Separate endpoints for KIS)
        self.ws_url_tick: Optional[str] = None
        self.ws_url_orderbook: Optional[str] = None

        self.tick_tr_ids = {'H0STCNT0', 'HDFSCNT0'}
        self.orderbook_tr_ids = {'H0STASP0', 'HDFSASP0', 'HHDFS00000300'} # Add legacy/fallback IDs if needed
        
        # Auto-Refresh Callback
        self.key_refresh_callback = None
        self.last_refresh_time = 0

    def set_refresh_callback(self, callback):
        """Set callback for auto key refresh"""
        self.key_refresh_callback = callback
        
    async def trigger_refresh(self):
        """Trigger key refresh with cooldown"""
        import time
        now = time.time()
        if now - self.last_refresh_time < 60: # 60s Cooldown
            logger.warning("⏳ Key refresh cooldown active. Skipping.")
            return

        if self.key_refresh_callback:
            self.last_refresh_time = now
            logger.info("♻️  Executing Key Refresh Callback...")
            await self.key_refresh_callback()
        else:
            logger.error("❌ No key_refresh_callback set!")

    async def connect_redis(self):
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        logger.info("✅ Redis Connected")
        await self.raw_logger.start()

    def _determine_socket_type(self, tr_id: str) -> str:
        """Returns 'tick' or 'orderbook' or 'unknown'"""
        if tr_id in self.tick_tr_ids:
            return 'tick'
        if tr_id in self.orderbook_tr_ids:
            return 'orderbook'
        # Default fallback: inspect format or assume Tick if it looks like execution?
        # For safety, log warning and default to orderbook (less risky for latency)?
        # Actually, let's look at the tr_id strictly.
        return 'unknown'

    async def _handle_message(self, message: str, source: str) -> Optional[str]:
        """Generic message handler for both sockets"""
        # PINGPONG Check First (Fast Path)
        if message[0] not in ['0', '1']:
            # PINGPONG Check
            if '"tr_id":"PINGPONG"' in message:
                return "PONG"

            # Protocol Error Check (JSON)
            if message.startswith('{'):
                try:
                    data = json.loads(message)
                    # Check for KIS Error Format
                    # Usually found in body -> msg1 or msg_cd
                    if 'body' in data:
                        body_data = data['body']
                        msg = body_data.get('msg1') or body_data.get('msg_cd')
                        if msg:
                            # 🚨 KEY EXPIRED DETECTION
                            if "invalid tr_key" in msg or "Expired" in msg:
                                logger.error("🚨 DETECTED INVALID KEY! Triggering Auto-Refresh...")
                                await self._publish_alert("CRITICAL", f"KIS Key Expired: {msg}")
                                asyncio.create_task(self.trigger_refresh())
                                return "ERROR"
                            
                            # ✅ SUCCESS DETECTION
                            if "SUBSCRIBE SUCCESS" in msg:
                                logger.info(f"✅ [SUCCESS] {source.upper()}: {msg}")
                                return "SUCCESS"
                            
                            # 🚨 CRITICAL PROTOCOL ERRORS
                            if "ALREADY IN USE" in msg:
                                logger.critical(f"🚨 DUPLICATE CONNECTION: {msg}")
                                await self._publish_alert("CRITICAL", f"KIS Connection Conflict: {msg}")
                                return "ERROR"

                            logger.error(f"🚨 PROTOCOL ERROR [{source.upper()}]: {msg} | Raw: {message}")
                            await self._publish_alert("ERROR", f"KIS Protocol Error: {msg}")
                            return "ERROR"
                except json.JSONDecodeError:
                    pass
            
            return None

        # Logging (Sampled or Full)
        await self.raw_logger.log(message, direction="RX") # Enabled for debugging/persistence

        parts = message.split('|')
        if len(parts) < 4:
            return None

        tr_id = parts[1]
        body = parts[3]
        
        collector = self.collectors.get(tr_id)
        if collector:
            # Delegate Parsing
            data_obj = collector.parse_tick(body)
            if data_obj and self.redis:
                channel = collector.get_channel()
                await self.redis.publish(channel, data_obj.model_dump_json())
                
                # Simple Logging (prevent flood)
                # logger.debug(f"[{source.upper()}] PUSH: {data_obj.symbol}")
        
        return tr_id

    async def _send_request(self, socket_type: str, tr_id: str, tr_key: str, tr_type: str):
        """Routes request to the correct socket"""
        target_ws = None
        target_lock = None
        
        if socket_type == 'tick':
            target_ws = self.ws_tick
            target_lock = self.lock_tick
        elif socket_type == 'orderbook':
            target_ws = self.ws_orderbook
            target_lock = self.lock_orderbook
            
        if not target_ws:
            logger.warning(f"⚠️  Cannot send request: {socket_type} socket not connected.")
            return

        async with target_lock:
            if not target_ws or not self.approval_key:
                return
            
            req = {
                # KIS WebSocket Header (Add encrypt: N)
                "header": {
                    "approval_key": self.approval_key,
                    "custtype": "P",
                    "tr_type": tr_type,
                    "content-type": "utf-8",
                    "encrypt": "N"  # Required for KIS
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": tr_key
                    }
                }
            }
            await target_ws.send(json.dumps(req))
            logger.info(f"📤 SENT [{socket_type.upper()}]: tr_id={tr_id} key={tr_key} type={tr_type}")

    async def subscribe_market(self, market: str):
        """Subscribes to all collectors for the given market, routing appropriately"""
        if market in self.active_markets:
            return

        logger.info(f"[{market}] Starting DUAL-SOCKET Subscription...")
        
        for tr_id, collector in self.collectors.items():
            if collector.market == market:
                # Load Symbols
                if not collector.symbols:
                    collector.load_symbols()
                
                # Determine Socket Type
                socket_type = self._determine_socket_type(tr_id)
                if socket_type == 'unknown':
                    logger.warning(f"❌ Unknown TR_ID type {tr_id}, skipping subscription.")
                    continue
                
                for sym in collector.symbols:
                    await self._send_request(socket_type, tr_id, sym, "1") # 1=Subscribe
                    await asyncio.sleep(0.5) # Safer rate limit (KIS TPS is strict)
        
        self.active_markets.add(market)
        logger.info(f"[{market}] Subscription Setup Complete.")

    async def unsubscribe_market(self, market: str):
        """Unsubscribes, routing appropriately"""
        if market not in self.active_markets:
            return
            
        logger.info(f"[{market}] Unsubscribing...")
        for tr_id, collector in self.collectors.items():
            if collector.market == market:
                socket_type = self._determine_socket_type(tr_id)
                if socket_type == 'unknown': continue

                for sym in collector.symbols:
                    await self._send_request(socket_type, tr_id, sym, "2")
                    await asyncio.sleep(0.1)
        
        self.active_markets.discard(market)

    async def _maintain_connection(self, socket_type: str):
        """Dedicated loop for a single socket connection"""
        while True:
            try:
                target_url = self.ws_url_tick if socket_type == 'tick' else self.ws_url_orderbook
                if not target_url:
                    logger.warning(f"⚠️  No URL set for {socket_type} socket. Waiting...")
                    await asyncio.sleep(5)
                    continue

                logger.info(f"🔌 [{socket_type.upper()}] Connecting to {target_url}...")
                
                # Enhanced connection with explicit heartbeat
                async with websockets.connect(
                    target_url,
                    ping_interval=30,      # Send ping every 30 seconds
                    ping_timeout=10,       # Wait 10s for pong response
                    close_timeout=10,      # Wait 10s for close frame
                    max_size=10_000_000,   # 10MB max message size
                    compression=None       # Disable compression for lower latency
                ) as ws:
                    logger.info(f"✅ [{socket_type.upper()}] Connected.")
                    
                    # Update State
                    if socket_type == 'tick':
                        async with self.lock_tick: self.ws_tick = ws
                    else:
                        async with self.lock_orderbook: self.ws_orderbook = ws
                    
                    # ✅ Auto-Resubscribe Logic
                    logger.info(f"🔄 [{socket_type.upper()}] Re-subscribing to {len(self.active_markets)} active markets...")
                    for market in list(self.active_markets):
                         # We call internal logical sender to avoid 'already active' check
                         for tr_id, collector in self.collectors.items():
                            if collector.market == market:
                                detected_type = self._determine_socket_type(tr_id)
                                if detected_type == socket_type:
                                    for sym in collector.symbols:
                                        await self._send_request(socket_type, tr_id, sym, "1")
                                        await asyncio.sleep(0.01) # Faster recovery
                    
                    async for message in ws:
                        res = await self._handle_message(message, socket_type)
                        if res == "PONG":
                            await ws.send(message)
                            
            except Exception as e:
                logger.error(f"⚠️ [{socket_type.upper()}] Error: {e}")
                
            finally:
                # Cleanup
                if socket_type == 'tick':
                    async with self.lock_tick: self.ws_tick = None
                else:
                    async with self.lock_orderbook: self.ws_orderbook = None
                
                await asyncio.sleep(5) # Reconnect delay

    async def switch_urls(self, tick_url: str, orderbook_url: str):
        """Updates the URLs and forces reconnection for both sockets."""
        logger.info(f"🔄 Switching Dual-Socket URLs to: Tick={tick_url}, Orderbook={orderbook_url}")
        self.ws_url_tick = tick_url
        self.ws_url_orderbook = orderbook_url
        
        # Force Close to trigger reconnect loop
        if self.ws_tick:
            await self.ws_tick.close()
        if self.ws_orderbook:
            await self.ws_orderbook.close()

    async def run(self, tick_url: str, orderbook_url: Optional[str] = None, approval_key: Optional[str] = None):
        """Main entry point: Launches parallel connection loops"""
        self.approval_key = approval_key
        self.ws_url_tick = tick_url
        self.ws_url_orderbook = orderbook_url or tick_url
        
        await self.connect_redis()
        
        # Load Symbols
        for c in self.collectors.values():
            c.load_symbols()
            logger.info(f"[{c.market}] Loaded {len(c.symbols)} symbols for {c.tr_id}")

        # Run sockets based on active collectors
        tasks = []
        if any(self._determine_socket_type(tr_id) == 'tick' for tr_id in self.collectors):
            tasks.append(self._maintain_connection('tick'))
        
        if any(self._determine_socket_type(tr_id) == 'orderbook' for tr_id in self.collectors):
            tasks.append(self._delayed_orderbook_start(5))

        if tasks:
            logger.info(f"🚀 Starting DUAL-SOCKET Manager with {len(tasks)} active sockets...")
            await asyncio.gather(*tasks)
        else:
            logger.error("❌ No valid collectors found. Manager exiting.")

    async def _publish_alert(self, level: str, message: str):
        """Publish system alert to Redis"""
        try:
            if self.redis:
                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "KIS-Service",
                    "level": level,
                    "message": message
                }
                await self.redis.publish("system:alerts", json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}")

    async def _delayed_orderbook_start(self, delay: int):
        """Start orderbook connection after a delay to prevent KIS key conflicts"""
        await asyncio.sleep(delay)
        await self._maintain_connection('orderbook')
