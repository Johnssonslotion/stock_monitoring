"""
Virtual Investment API Routes
Provides REST endpoints for virtual trading operations.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

from src.broker.virtual import VirtualExchange
from src.broker.base import Order
from ..auth import verify_api_key

router = APIRouter(
    prefix="/api/virtual",
    tags=["virtual"],
    dependencies=[Depends(verify_api_key)]
)

# Pydantic Models
class OrderRequest(BaseModel):
    symbol: str
    side: str  # BUY/SELL
    type: str  # LIMIT/MARKET
    quantity: int
    price: Optional[float] = None

class AccountResponse(BaseModel):
    account_id: int
    name: str
    balance: float
    currency: str
    created_at: str
    updated_at: str

class PositionResponse(BaseModel):
    symbol: str
    quantity: int
    avg_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

# Global VirtualExchange instance (initialized on startup)
virtual_exchange: Optional[VirtualExchange] = None

def get_virtual_exchange() -> VirtualExchange:
    """Dependency to get VirtualExchange instance"""
    if not virtual_exchange:
        raise HTTPException(status_code=503, detail="Virtual Exchange not initialized")
    return virtual_exchange

@router.get("/account")
async def get_account(exchange: VirtualExchange = Depends(get_virtual_exchange)):
    """Get virtual account information"""
    try:
        balance = await exchange.get_balance()
        
        # Fetch account details from DB
        async with exchange.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, balance, currency, created_at, updated_at FROM virtual_accounts WHERE id = $1",
                exchange.account_id
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Account not found")
            
            return {
                "account_id": row['id'],
                "name": row['name'],
                "balance": float(row['balance']),
                "currency": row['currency'],
                "created_at": row['created_at'].isoformat(),
                "updated_at": row['updated_at'].isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions")
async def get_positions(
    symbol: Optional[str] = None,
    exchange: VirtualExchange = Depends(get_virtual_exchange)
):
    """Get current positions"""
    try:
        positions = await exchange.get_positions()
        
        # Filter by symbol if provided
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        
        # Calculate unrealized PnL (would need current market price - simplified for now)
        result = []
        total_value = 0.0
        
        for pos in positions:
            # TODO: Fetch current_price from Redis/DB
            current_price = pos.avg_price  # Placeholder
            unrealized_pnl = (current_price - pos.avg_price) * pos.quantity
            unrealized_pnl_pct = (unrealized_pnl / (pos.avg_price * pos.quantity)) * 100 if pos.avg_price > 0 else 0.0
            
            position_value = current_price * pos.quantity
            total_value += position_value
            
            result.append({
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct
            })
        
        return {
            "positions": result,
            "total_value": total_value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orders")
async def create_order(
    order_req: OrderRequest,
    exchange: VirtualExchange = Depends(get_virtual_exchange)
):
    """Create a new order"""
    try:
        # Validate
        if order_req.side not in ["BUY", "SELL"]:
            raise HTTPException(status_code=400, detail="Invalid side. Must be BUY or SELL")
        
        if order_req.type not in ["LIMIT", "MARKET"]:
            raise HTTPException(status_code=400, detail="Invalid type. Must be LIMIT or MARKET")
        
        if order_req.type == "LIMIT" and not order_req.price:
            raise HTTPException(status_code=400, detail="Price required for LIMIT orders")
        
        if order_req.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        
        # Create order object
        order = Order(
            symbol=order_req.symbol,
            side=order_req.side,
            type=order_req.type,
            quantity=order_req.quantity,
            price=order_req.price,
            timestamp=datetime.now()
        )
        
        # For MARKET orders, get current price from Redis/DB
        market_price = None
        if order_req.type == "MARKET":
            # TODO: Fetch from Redis ticker or DB
            # For now, use price if provided, else reject
            if not order_req.price:
                raise HTTPException(
                    status_code=400, 
                    detail="Market price not available. Please provide price or use LIMIT order"
                )
            market_price = order_req.price
        
        # Execute order
        result = await exchange.place_order(order, market_price=market_price)
        
        # Check if rejected
        if result.get("status") == "REJECTED":
            raise HTTPException(status_code=400, detail=result.get("reason", "Order rejected"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders")
async def get_orders(
    limit: int = 50,
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    exchange: VirtualExchange = Depends(get_virtual_exchange)
):
    """Get order history"""
    try:
        query = """
            SELECT order_id, symbol, side, type, price, quantity, status,
                   filled_price, filled_quantity, fee, tax, created_at, executed_at
            FROM virtual_orders
            WHERE account_id = $1
        """
        params = [exchange.account_id]
        
        if symbol:
            query += f" AND symbol = ${len(params) + 1}"
            params.append(symbol)
        
        if status:
            query += f" AND status = ${len(params) + 1}"
            params.append(status)
        
        query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        async with exchange.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            orders = []
            for row in rows:
                orders.append({
                    "order_id": row['order_id'],
                    "symbol": row['symbol'],
                    "side": row['side'],
                    "type": row['type'],
                    "price": float(row['price']) if row['price'] else None,
                    "quantity": row['quantity'],
                    "status": row['status'],
                    "filled_price": float(row['filled_price']) if row['filled_price'] else None,
                    "filled_quantity": row['filled_quantity'],
                    "fee": float(row['fee']) if row['fee'] else 0.0,
                    "tax": float(row['tax']) if row['tax'] else 0.0,
                    "created_at": row['created_at'].isoformat(),
                    "executed_at": row['executed_at'].isoformat() if row['executed_at'] else None
                })
            
            return {
                "orders": orders,
                "total": len(orders)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    exchange: VirtualExchange = Depends(get_virtual_exchange)
):
    """Get specific order details"""
    try:
        async with exchange.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT order_id, symbol, side, type, price, quantity, status,
                       filled_price, filled_quantity, fee, tax, created_at, executed_at
                FROM virtual_orders
                WHERE order_id = $1 AND account_id = $2
            """, order_id, exchange.account_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Order not found")
            
            return {
                "order_id": row['order_id'],
                "symbol": row['symbol'],
                "side": row['side'],
                "type": row['type'],
                "price": float(row['price']) if row['price'] else None,
                "quantity": row['quantity'],
                "status": row['status'],
                "filled_price": float(row['filled_price']) if row['filled_price'] else None,
                "filled_quantity": row['filled_quantity'],
                "commission": float(row['fee']) if row['fee'] else 0.0,
                "tax": float(row['tax']) if row['tax'] else 0.0,
                "created_at": row['created_at'].isoformat(),
                "executed_at": row['executed_at'].isoformat() if row['executed_at'] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pnl")
async def get_pnl(
    period: str = "all",
    exchange: VirtualExchange = Depends(get_virtual_exchange)
):
    """Get Profit & Loss analysis"""
    try:
        # Simplified PnL calculation
        # In production, should track realized PnL from closed positions
        
        async with exchange.pool.acquire() as conn:
            # Get all filled orders
            rows = await conn.fetch("""
                SELECT side, filled_price, filled_quantity, fee, tax
                FROM virtual_orders
                WHERE account_id = $1 AND status = 'FILLED'
                ORDER BY executed_at ASC
            """, exchange.account_id)
            
            # Calculate realized PnL (simplified - matching buy/sell pairs)
            realized_pnl = 0.0
            total_trades = len(rows)
            wins = 0
            
            # Get unrealized PnL from positions
            positions = await exchange.get_positions()
            unrealized_pnl = 0.0
            for pos in positions:
                # TODO: Get current price
                current_price = pos.avg_price
                unrealized_pnl += (current_price - pos.avg_price) * pos.quantity
            
            # Get initial balance
            account_row = await conn.fetchrow(
                "SELECT balance FROM virtual_accounts WHERE id = $1",
                exchange.account_id
            )
            initial_balance = 100_000_000.0  # Hardcoded for now
            current_balance = float(account_row['balance']) if account_row else 0.0
            
            total_pnl = realized_pnl + unrealized_pnl
            total_pnl_pct = (total_pnl / initial_balance) * 100 if initial_balance > 0 else 0.0
            
            return {
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "total_pnl": total_pnl,
                "total_pnl_pct": total_pnl_pct,
                "total_trades": total_trades,
                "win_rate": 0.0,  # TODO: Calculate properly
                "period_start": None,  # TODO: Based on period param
                "period_end": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
