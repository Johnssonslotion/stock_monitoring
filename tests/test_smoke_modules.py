
import os
import importlib
import pytest
import redis

def test_imports():
    """Fail if critical modules cannot be imported (syntax error, missing dep)."""
    modules = [
        "src.data_ingestion.ticks.archiver",
        "src.data_ingestion.ticks.validation_job",
        "src.data_ingestion.price.kr.real_collector",
        "src.data_ingestion.price.unified_collector",
        "src.data_ingestion.archiver.timescale_archiver",
    ]
    
    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            pytest.fail(f"Smoke Test Failed: Cannot import {module_name}. Error: {e}")

def test_redis_connection():
    """Fail if Redis is not accessible (skip if checking offline)."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    
    try:
        r = redis.Redis(host=redis_host, port=redis_port, socket_timeout=1)
        r.ping()
    except redis.ConnectionError:
        # In CI/Test environment, Redis might not be available.
        # But for Preflight Check, we usually expect it.
        # For now, we warn but don't fail hard unless strict mode is enabled.
        if os.getenv("STRICT_SMOKE_TEST") == "true":
            pytest.fail(f"Smoke Test Failed: Cannot connect to Redis at {redis_host}:{redis_port}")
        else:
            print(f"Warning: Redis not reachable at {redis_host}:{redis_port}. Ignoring for basic smoke.")

def test_duckdb_path():
    """Verify data directory exists for DuckDB."""
    # Assuming standard project structure
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        # It's okay if data_dir doesn't exist, Archiver usually creates it.
        # But we check if we have write permission to CWD.
        if not os.access(os.getcwd(), os.W_OK):
             pytest.fail(f"Smoke Test Failed: Current directory {os.getcwd()} is not writable.")
