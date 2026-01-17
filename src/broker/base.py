"""
Broker Interface
Defines the standard interface for all broker adapters (Real/Virtual).
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Order:
    symbol: str
    side: str  # BUY/SELL
    type: str  # LIMIT/MARKET
    quantity: int
    price: Optional[float] = None
    order_id: Optional[str] = None
    timestamp: Optional[datetime] = None

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    current_price: float = 0.0

class Broker(ABC):
    """Abstract Base Class for Broker Adapters"""
    
    @abstractmethod
    async def connect(self):
        """Connect to broker API or DB"""
        pass

    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance (Cash)"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        pass

    @abstractmethod
    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place an order"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
