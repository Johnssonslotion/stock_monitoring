from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import os
import json
from datetime import datetime
from typing import Optional, List, Dict

app = FastAPI(title="Antigravity External Health API", version="1.0.0")

# Security & CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
API_AUTH_SECRET = os.getenv("API_AUTH_SECRET", "super-secret-key")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# DB Config (Tailscale IP of A1)
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "stockval")

db_pool = None

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != API_AUTH_SECRET:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=int(DB_PORT)
    )

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/v1/status", dependencies=[Depends(verify_api_key)])
async def get_system_status():
    """Returns combined host metrics and container statuses from A1 DB"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="DB Connection not initialized")

    async with db_pool.acquire() as conn:
        # Get latest metrics per type
        rows = await conn.fetch("""
            WITH LatestMetrics AS (
                SELECT DISTINCT ON (type)
                    time, type, value, meta
                FROM system_metrics
                WHERE time > NOW() - INTERVAL '10 minutes'
                ORDER BY type, time DESC
            )
            SELECT * FROM LatestMetrics;
        """)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "infrastructure": {},
            "services": []
        }
        
        for r in rows:
            m_type = r['type']
            val = r['value']
            meta = json.loads(r['meta']) if r['meta'] else None
            
            if m_type in ['cpu', 'memory', 'disk']:
                results["infrastructure"][m_type] = val
            elif m_type == 'container_status':
                results["services"].append({
                    "name": meta.get("container") if meta else "unknown",
                    "status": meta.get("status") if meta else "unknown",
                    "is_running": val == 1.0,
                    "last_updated": r['time'].isoformat()
                })
        
        return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
