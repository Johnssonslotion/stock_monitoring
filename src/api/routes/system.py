from fastapi import APIRouter, Depends, HTTPException, Request
from ..auth import verify_api_key
from typing import List, Optional
from datetime import datetime
import json

router = APIRouter(
    prefix="/api/system",
    tags=["system"]
)

@router.get("/metrics")
async def get_system_metrics(request: Request, limit: int = 100):
    """
    최근 시스템 메트릭 조회 (CPU, Memory, Disk, Container Health)
    """
    if not hasattr(request.app.state, "db_pool") or not request.app.state.db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    pool = request.app.state.db_pool
    
    async with pool.acquire() as conn:
        # Fetch generic metrics
        rows = await conn.fetch("""
            SELECT time, type, value, meta
            FROM system_metrics
            ORDER BY time DESC
            LIMIT $1
        """, limit)
        
        results = []
        for r in rows:
            meta = json.loads(r['meta']) if r['meta'] else None
            results.append({
                "time": r['time'].isoformat(),
                "type": r['type'],
                "value": r['value'],
                "meta": meta
            })
            
        return results

@router.get("/governance/status")
async def get_governance_status():
    """
    거버넌스 준수 현황 조회 (인간이 수립한 문서 기반)
    """
    # 임시로 감사 결과 요약 반환 (향후 자동화 가능)
    return {
        "last_audit": "2026-01-17",
        "compliance_score": 95,
        "status": "Healthy",
        "p0_issues": 0,
        "p1_issues": 2, # DEF-002, DEF-003
        "workflows_active": 10,
        "constitution_version": "2.5"
    }

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@router.websocket("/ws")
async def system_websocket(websocket: WebSocket):
    """
    시스템 및 거버넌스 메트릭 실시간 스트리밍
    """
    await websocket.accept()
    
    r = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("system.metrics", "system_alerts")
    
    try:
        # 1. Initial State (Latest from DB)
        # TODO: Fetch last 10 metrics from DB if needed
        
        # 2. Stream Updates
        async for message in pubsub.listen():
            if message["type"] == "message":
                # Add type field for StreamManager.ts to identify
                raw_data = json.loads(message["data"])
                
                # Unify format: Add 'type' if missing
                if "type" not in raw_data and message["channel"] == "system.metrics":
                    # Backward compatibility or internal format
                    pass 
                
                await websocket.send_json({
                    "channel": message["channel"],
                    "data": raw_data
                })
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe()
        await r.close()
