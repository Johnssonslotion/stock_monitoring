"""
Integration tests for Virtual Investment API
Tests REST endpoints and order execution flows.
"""
import pytest
import httpx
from src.api.main import app
from src.api.routes import virtual
from src.broker.virtual import VirtualExchange
import os
import asyncpg
import asyncio
import json

# Test configuration
API_KEY = "super-secret-key"
HEADER = {"x-api-key": API_KEY}

# DB Config
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'database': os.getenv('DB_NAME', 'stockval'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432))
}

@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture(autouse=True)
async def setup_virtual_exchange():
    """Initialize VirtualExchange before tests"""
    # 1. Create Tables
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS virtual_accounts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            balance DECIMAL(20, 2) DEFAULT 0.00,
            currency VARCHAR(5) DEFAULT 'KRW',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS virtual_positions (
            account_id INT NOT NULL REFERENCES virtual_accounts(id),
            symbol VARCHAR(20) NOT NULL,
            quantity INT NOT NULL DEFAULT 0,
            avg_price DECIMAL(20, 4) DEFAULT 0.0000,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (account_id, symbol)
        );
        CREATE TABLE IF NOT EXISTS virtual_orders (
            order_id UUID PRIMARY KEY,
            account_id INT NOT NULL REFERENCES virtual_accounts(id),
            symbol VARCHAR(20) NOT NULL,
            side VARCHAR(4) NOT NULL,
            type VARCHAR(10) NOT NULL,
            price DECIMAL(20, 4),
            quantity INT NOT NULL,
            status VARCHAR(20) DEFAULT 'PENDING',
            filled_price DECIMAL(20, 4),
            filled_quantity INT DEFAULT 0,
            fee DECIMAL(20, 4) DEFAULT 0.00,
            tax DECIMAL(20, 4) DEFAULT 0.00,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            executed_at TIMESTAMPTZ
        );
    """)
    await conn.close()
    
    # 2. Init VirtualExchange
    virtual.virtual_exchange = VirtualExchange(DB_CONFIG, account_id=999)
    await virtual.virtual_exchange.connect()
    
    yield
    
    # Cleanup
    if virtual.virtual_exchange:
        await virtual.virtual_exchange.close()

@pytest.mark.asyncio
async def test_virtual_account(async_client):
    """Test GET /api/virtual/account"""
    response = await async_client.get("/api/virtual/account", headers=HEADER)
    assert response.status_code == 200
    data = response.json()
    assert "account_id" in data
    assert data["account_id"] == 999

@pytest.mark.asyncio
async def test_virtual_positions(async_client):
    """Test GET /api/virtual/positions"""
    response = await async_client.get("/api/virtual/positions", headers=HEADER)
    assert response.status_code == 200
    data = response.json()
    assert "positions" in data

@pytest.mark.asyncio
async def test_create_buy_order(async_client):
    """Test POST /api/virtual/orders - BUY"""
    order_data = {
        "symbol": "005930",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": 5,
        "price": 71000.0
    }
    
    response = await async_client.post("/api/virtual/orders", json=order_data, headers=HEADER)
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["status"] == "FILLED"

@pytest.mark.asyncio
async def test_get_orders_history(async_client):
    """Test GET /api/virtual/orders"""
    response = await async_client.get("/api/virtual/orders?limit=10", headers=HEADER)
    assert response.status_code == 200
    data = response.json()
    assert "orders" in data

@pytest.mark.asyncio
async def test_get_pnl(async_client):
    """Test GET /api/virtual/pnl"""
    response = await async_client.get("/api/virtual/pnl", headers=HEADER)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_order_validation(async_client):
    """Test order input validation"""
    invalid_order = {
        "symbol": "005930",
        "side": "INVALID",
        "type": "LIMIT",
        "quantity": 10,
        "price": 70000.0
    }
    
    response = await async_client.post("/api/virtual/orders", json=invalid_order, headers=HEADER)
    assert response.status_code == 400
