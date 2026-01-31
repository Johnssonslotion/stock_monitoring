import pytest
import redis.asyncio as redis
import json
import asyncio
import os
import asyncpg
from fastapi.testclient import TestClient
from src.api.main import app
from datetime import datetime, timezone

# 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_AUTH_SECRET = os.getenv("API_AUTH_SECRET", "super-secret-key")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "stockval")

@pytest.mark.asyncio
async def test_system_dashboard_e2e():
    """Sentinel(Sim) -> Redis -> Archiver -> DB -> API -> Dashboard Data Verification"""
    
    # 1. Simulate Sentinel Publishing
    r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    
    test_cpu_val = 99.9
    container_name = "e2e-test-container"
    
    payload_host = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "cpu",
        "value": test_cpu_val,
        "meta": None
    }
    
    payload_container = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "container_status",
        "value": 1.0, # Running
        "meta": {"container": container_name, "status": "running"}
    }
    
    # Publish to shared channel
    await r.publish("system.metrics", json.dumps(payload_host))
    await r.publish("system.metrics", json.dumps(payload_container))
    await r.close()
    
    # 2. Wait for Archiver persistence
    conn = await asyncpg.connect(user="postgres", password="password", database=DB_NAME, host=DB_HOST)
    
    found_host = False
    found_container = False
    
    for _ in range(10): # 5s timeout
        # Check Host Metric
        row_host = await conn.fetchrow(
            "SELECT * FROM system_metrics WHERE metric_name = 'cpu' AND value = $1 ORDER BY time DESC LIMIT 1", 
            test_cpu_val
        )
        if row_host: found_host = True
        
        # Check Container Metric (Meta field JSON query)
        row_cont = await conn.fetchrow(
            "SELECT * FROM system_metrics WHERE metric_name = 'container_status' AND labels->>'container' = $1", 
            container_name
        )
        if row_cont: found_container = True
        
        if found_host and found_container:
            break
            
        await asyncio.sleep(0.5)
        
    await conn.close()
    
    assert found_host, "Host Metric (CPU) failed to survive the pipeline"
    assert found_container, "Container Status Metric failed to survive the pipeline"
    
    # 3. Verify API Response (Dashboard Data Source)
    with TestClient(app) as client:
        response = client.get(
            "/api/system/metrics",
            headers={"x-api-key": API_AUTH_SECRET},
            params={"limit": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Host Metric in Response
        api_host = next((d for d in data if d["type"] == "cpu" and d["value"] == test_cpu_val), None)
        assert api_host is not None, "API Response missing the injected CPU metric"
        
        # Verify Container Metric in Response
        api_cont = next((d for d in data if d["type"] == "container_status" and d["meta"] and d["meta"].get("container") == container_name), None)
        assert api_cont is not None, "API Response missing the injected Container metric"
        assert api_cont["meta"]["status"] == "running"
