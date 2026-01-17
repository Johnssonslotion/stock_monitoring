"""
Integration tests for Virtual Investment API
Tests REST endpoints and order execution flows.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routes import virtual
from src.broker.virtual import VirtualExchange
import os

# Test configuration
API_KEY = "super-secret-key"

# DB Config
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'database': os.getenv('DB_NAME', 'stock_test'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432))
}

@pytest.fixture(scope="module", autouse=True)
def setup_virtual_exchange():
    """Initialize VirtualExchange before tests"""
    import asyncio
    
    async def init():
        virtual.virtual_exchange = VirtualExchange(DB_CONFIG, account_id=999)  # Test account
        await virtual.virtual_exchange.connect()
    
    asyncio.run(init())
    yield
    
    async def cleanup():
        if virtual.virtual_exchange:
            await virtual.virtual_exchange.close()
    
    asyncio.run(cleanup())

client = TestClient(app)

def test_virtual_account():
    """Test GET /api/virtual/account"""
    response = client.get(
        "/api/virtual/account",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "account_id" in data
    assert "balance" in data
    assert data["currency"] == "KRW"

def test_virtual_positions():
    """Test GET /api/virtual/positions"""
    response = client.get(
        "/api/virtual/positions",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "positions" in data
    assert "total_value" in data
    assert isinstance(data["positions"], list)

def test_create_buy_order():
    """Test POST /api/virtual/orders - BUY"""
    order_data = {
        "symbol": "005930",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": 5,
        "price": 71000.0
    }
    
    response = client.post(
        "/api/virtual/orders",
        json=order_data,
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["status"] == "FILLED"
    assert data["filled_quantity"] == 5
    assert "commission" in data
    assert float(data["commission"]) > 0  # Should have commission

def test_get_orders_history():
    """Test GET /api/virtual/orders"""
    response = client.get(
        "/api/virtual/orders?limit=10",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "orders" in data
    assert "total" in data
    assert isinstance(data["orders"], list)

def test_get_pnl():
    """Test GET /api/virtual/pnl"""
    response = client.get("/api/virtual/pnl", headers={"Authorization": f"Bearer {API_KEY}"})
    
    assert response.status_code == 200
    data = response.json()
    assert "realized_pnl" in data
    assert "unrealized_pnl" in data
    assert "total_pnl" in data

def test_order_validation():
    """Test order input validation"""
    invalid_order = {
        "symbol": "005930",
        "side": "INVALID",
        "type": "LIMIT",
        "quantity": 10,
        "price": 70000.0
    }
    
    response = client.post(
        "/api/virtual/orders",
        json=invalid_order,
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    assert response.status_code == 400
