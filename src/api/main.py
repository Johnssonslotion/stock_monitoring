from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import asyncio
import json
import os
import logging
from typing import List

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI()

# CORS for Electron App (Localhost development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        # Broadcast to all connected clients
        # Use a copy of the list to avoid modification during iteration issues if disconnect happens
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_subscriber())

async def redis_subscriber():
    """
    Subscribe to Redis 'tick.*' and broadcast via WebSocket
    """
    try:
        r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.psubscribe("tick.*")
        logger.info("Connected to Redis Pub/Sub")

        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                data = message["data"]
                # Forward to all WebSocket clients
                await manager.broadcast(data)
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, maybe receive commands from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
@app.get("/health")
async def health_check():
    return {"status": "ok"}
