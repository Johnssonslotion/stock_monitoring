"""
Virtual Exchange Implementation
Simulates a real broker execution environment with realistic cost modeling.
"""
import uuid
import logging
import asyncpg
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Any, Optional

import os
import redis.asyncio as redis

from .base import Broker, Order, Position
from .cost_model import CostCalculator, CostConfig

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class VirtualExchange(Broker):
    """
    Virtual Exchange Adapter
    
    Features:
    - Simulates order execution against current market price (or passed price)
    - Calculates Taxes, Commissions, and Interest
    - Persists state to 'virtual_*' tables in DB
    """
    
    def __init__(self, db_config: Dict[str, Any], account_id: int = 1):
        self.db_config = db_config
        self.account_id = account_id
        self.pool = None
        self.redis = None
        self.cost_calculator = CostCalculator(CostConfig()) # Default Config

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                user=self.db_config.get('user', 'postgres'),
                password=self.db_config.get('password', 'password'),
                database=self.db_config.get('database', 'stock_test'),
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432)
            )
            # Ensure account exists
            await self._ensure_account()
            
        if not self.redis:
            self.redis = await redis.from_url(REDIS_URL, decode_responses=True)

    async def close(self):
        if self.pool:
            await self.pool.close()
        if self.redis:
            await self.redis.close()

    async def _ensure_account(self):
        """계좌 존재 여부 확인 및 생성"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT id FROM virtual_accounts WHERE id = $1", self.account_id)
            if not row:
                await conn.execute("""
                    INSERT INTO virtual_accounts (id, name, balance, currency)
                    VALUES ($1, $2, $3, $4)
                """, self.account_id, "Virtual Account 01", 100_000_000.0, "KRW")
                logger.info(f"Created virtual account {self.account_id} with 100M KRW")

    async def get_balance(self) -> Dict[str, float]:
        if not self.pool: await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT balance FROM virtual_accounts WHERE id = $1", self.account_id)
            return {"KRW": float(row['balance']) if row else 0.0}

    async def get_positions(self) -> List[Position]:
        if not self.pool: await self.connect()
        positions = []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT symbol, quantity, avg_price FROM virtual_positions WHERE account_id = $1", self.account_id)
            for row in rows:
                positions.append(Position(
                    symbol=row['symbol'],
                    quantity=row['quantity'],
                    avg_price=float(row['avg_price'])
                ))
        return positions

    async def place_order(self, order: Order, market_price: float = None) -> Dict[str, Any]:
        """
        주문 실행 및 체결 (Simplified: Market/Limit 모두 즉시 체결 시도)
        Real implementation should separate Place -> Match -> Fill
        But for MVP, we assume immediate fill if price condition met.
        """
        if not self.pool: await self.connect()
        
        # 1. Determine Execution Price
        exec_price = Decimal(str(market_price if market_price else order.price))
        if order.type == 'MARKET' and not market_price:
            raise ValueError("Market price required for MARKET order simulation")
            
        # 2. Calculate Costs
        costs = self.cost_calculator.calculate_total_cost(exec_price, order.quantity, order.side)
        total_fill_amt = exec_price * order.quantity
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Check Balance (BUY) or Position (SELL)
                balance_row = await conn.fetchrow("SELECT balance FROM virtual_accounts WHERE id = $1 FOR UPDATE", self.account_id)
                current_balance = Decimal(str(balance_row['balance']))
                
                if order.side == "BUY":
                    required_amt = total_fill_amt + costs['commission'] # No tax on buy
                    if current_balance < required_amt:
                        return {"status": "REJECTED", "reason": "Insufficient Funds"}
                    
                    # Deduct Balance
                    new_balance = current_balance - required_amt
                    await conn.execute("UPDATE virtual_accounts SET balance = $1 WHERE id = $2", float(new_balance), self.account_id)
                    
                    # Update Position
                    pos_row = await conn.fetchrow("SELECT quantity, avg_price FROM virtual_positions WHERE account_id=$1 AND symbol=$2", self.account_id, order.symbol)
                    if pos_row:
                        old_qty = pos_row['quantity']
                        old_avg = Decimal(str(pos_row['avg_price']))
                        new_qty = old_qty + order.quantity
                        new_avg = ((old_avg * old_qty) + total_fill_amt) / new_qty
                        await conn.execute("UPDATE virtual_positions SET quantity=$1, avg_price=$2 WHERE account_id=$3 AND symbol=$4",
                                           new_qty, float(new_avg), self.account_id, order.symbol)
                    else:
                        await conn.execute("INSERT INTO virtual_positions (account_id, symbol, quantity, avg_price) VALUES ($1, $2, $3, $4)",
                                           self.account_id, order.symbol, order.quantity, float(exec_price))
                                           
                elif order.side == "SELL":
                    pos_row = await conn.fetchrow("SELECT quantity FROM virtual_positions WHERE account_id=$1 AND symbol=$2 FOR UPDATE", self.account_id, order.symbol)
                    if not pos_row or pos_row['quantity'] < order.quantity:
                        return {"status": "REJECTED", "reason": "Insufficient Position"}
                    
                    # Add Balance (Net Proceed)
                    net_proceed = total_fill_amt - costs['total'] # Comm + Tax
                    new_balance = current_balance + net_proceed
                    await conn.execute("UPDATE virtual_accounts SET balance = $1 WHERE id = $2", float(new_balance), self.account_id)
                    
                    # Update Position
                    new_qty = pos_row['quantity'] - order.quantity
                    if new_qty > 0:
                        await conn.execute("UPDATE virtual_positions SET quantity=$1 WHERE account_id=$2 AND symbol=$3", new_qty, self.account_id, order.symbol)
                    else:
                        await conn.execute("DELETE FROM virtual_positions WHERE account_id=$1 AND symbol=$2", self.account_id, order.symbol)

                # Record Order
                order_uid = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO virtual_orders (order_id, account_id, symbol, side, type, price, quantity, status, filled_price, filled_quantity, fee, tax, executed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, 'FILLED', $8, $9, $10, $11, NOW())
                """, order_uid, self.account_id, order.symbol, order.side, order.type, float(order.price) if order.price else None, 
                   order.quantity, float(exec_price), order.quantity, float(costs['commission']), float(costs['tax']))
                   
                # Prepare Result
                result = {
                    "status": "FILLED",
                    "order_id": order_uid,
                    "filled_price": float(exec_price),
                    "filled_quantity": order.quantity,
                    "commission": float(costs['commission']),
                    "tax": float(costs['tax']),
                    "timestamp": datetime.now().isoformat()
                }

                # Publish Events
                if self.redis:
                    # 1. Execution Event
                    await self.redis.publish("virtual.execution", json.dumps({
                        "type": "EXECUTION",
                        "data": result,
                        "symbol": order.symbol,
                        "side": order.side
                    }))
                    
                    # 2. Account Update Event
                    account_state = {
                        "balance": float(new_balance),
                        "currency": "KRW",
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.redis.publish("virtual.account", json.dumps({
                        "type": "BALANCE",
                        "data": account_state
                    }))

                return result

    async def cancel_order(self, order_id: str) -> bool:
        # MVP: Immediate fill only, so cancellation is not supported yet
        return False
