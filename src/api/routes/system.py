from fastapi import APIRouter, Depends, HTTPException, Request
from ..auth import verify_api_key
from typing import List, Optional
from datetime import datetime
import json

router = APIRouter(
    prefix="/api/system",
    tags=["system"],
    dependencies=[Depends(verify_api_key)]
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
