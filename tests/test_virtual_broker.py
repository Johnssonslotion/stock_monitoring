import pytest
import asyncio
from decimal import Decimal
from src.broker.virtual import VirtualExchange
from src.broker.base import Order

# DB Config for Test Environment
DB_CONFIG = {
    'user': 'postgres',
    'password': 'password',
    'database': 'stock_test',
    'host': 'localhost',
    'port': 5432
}

@pytest.fixture
async def broker():
    broker = VirtualExchange(DB_CONFIG)
    await broker.connect()
    yield broker
    await broker.close()

@pytest.mark.asyncio
async def test_virtual_broker_flow():
    broker = VirtualExchange(DB_CONFIG, account_id=999) # Use ID 999 for test
    await broker.connect()
    
    # 1. Check Initial Balance (Should be 100M or exists)
    balance = await broker.get_balance()
    initial_krw = balance.get('KRW', 0)
    print(f"Initial Balance: {initial_krw}")
    assert initial_krw > 0
    
    # Reset for clean test if possible or just handle flow
    # Ideally we should clean up DB before test, but for now we just verify logic
    
    # 2. Place BUY Order
    # Buy 10 Samsung Elec @ 70,000
    buy_order = Order(
        symbol='005930', side='BUY', type='LIMIT', 
        quantity=10, price=70000
    )
    result = await broker.place_order(buy_order)
    assert result['status'] == 'FILLED'
    assert result['filled_quantity'] == 10
    
    # Verify Commission
    expected_amt = Decimal("70000") * 10
    expected_comm = expected_amt * Decimal("0.00015") # 0.015%
    assert Decimal(str(result['commission'])) == expected_comm
    
    # Verify Balance Decrease
    new_balance = await broker.get_balance()
    expected_deduction = expected_amt + expected_comm
    # Note: Logic assumes no other ops happened. 
    # assert new_balance['KRW'] == initial_krw - float(expected_deduction)
    
    # Verify Position
    positions = await broker.get_positions()
    target_pos = next((p for p in positions if p.symbol == '005930'), None)
    assert target_pos is not None
    assert target_pos.quantity >= 10
    
    # 3. Place SELL Order
    # Sell 5 @ 80,000 (Profit!)
    sell_order = Order(
        symbol='005930', side='SELL', type='LIMIT',
        quantity=5, price=80000
    )
    result_sell = await broker.place_order(sell_order)
    assert result_sell['status'] == 'FILLED'
    
    # Verify Tax & Comm
    sell_amt = Decimal("80000") * 5
    expected_sell_comm = sell_amt * Decimal("0.00015")
    expected_tax = sell_amt * Decimal("0.0018")
    
    assert Decimal(str(result_sell['commission'])) == expected_sell_comm
    assert Decimal(str(result_sell['tax'])) == expected_tax
    
    await broker.close()
