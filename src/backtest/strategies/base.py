"""전략 베이스 클래스 (Abstract Base Class)

모든 백테스팅 전략은 이 클래스를 상속받아 구현해야 합니다.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderSide(Enum):
    """주문 방향"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """주문 타입"""
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class Signal:
    """매매 신호"""
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    reason: str = ""  # 신호 발생 이유 (로깅용)


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    
    @property
    def market_value(self) -> float:
        """현재 시장 가치"""
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        """미실현 손익"""
        return (self.current_price - self.avg_price) * self.quantity
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """미실현 손익률 (%)"""
        if self.avg_price == 0:
            return 0.0
        return ((self.current_price - self.avg_price) / self.avg_price) * 100


class Strategy(ABC):
    """전략 베이스 클래스
    
    모든 백테스팅 전략은 이 클래스를 상속받아 구현합니다.
    
    Example:
        ```python
        class MomentumStrategy(Strategy):
            def __init__(self, window: int = 20, threshold: float = 0.02):
                super().__init__()
                self.window = window
                self.threshold = threshold
                self.price_history = []
            
            async def on_tick(self, tick_data: dict):
                self.price_history.append(tick_data['price'])
                if len(self.price_history) > self.window:
                    self.price_history.pop(0)
            
            def generate_signals(self) -> List[Signal]:
                if len(self.price_history) < self.window:
                    return []
                
                avg_price = sum(self.price_history) / len(self.price_history)
                current_price = self.price_history[-1]
                
                if current_price > avg_price * (1 + self.threshold):
                    return [Signal(
                        timestamp=datetime.now(),
                        symbol="005930",
                        side=OrderSide.BUY,
                        quantity=10,
                        reason=f"Price {current_price} > MA {avg_price}"
                    )]
                return []
        ```
    """
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.cash: float = 0.0
        self.initial_capital: float = 0.0
    
    @abstractmethod
    async def on_tick(self, tick_data: dict):
        """틱 데이터 수신 시 호출
        
        Args:
            tick_data: 틱 데이터 딕셔너리
                {
                    'timestamp': datetime,
                    'symbol': str,
                    'price': float,
                    'volume': int,
                    'market': str  # 'KR' or 'US'
                }
        """
        pass
    
    @abstractmethod
    def generate_signals(self) -> List[Signal]:
        """매매 신호 생성
        
        현재 상태를 기반으로 매매 신호를 생성합니다.
        
        Returns:
            List[Signal]: 생성된 매매 신호 리스트
        """
        pass
    
    def on_order_filled(self, signal: Signal, fill_price: float):
        """주문 체결 시 호출 (Optional)
        
        백테스팅 엔진이 주문을 체결한 후 이 메서드를 호출합니다.
        전략에서 포지션 관리를 직접 하려면 오버라이드하세요.
        
        Args:
            signal: 체결된 신호
            fill_price: 체결 가격
        """
        pass
    
    def update_position(self, symbol: str, current_price: float):
        """포지션 현재가 업데이트
        
        Args:
            symbol: 심볼
            current_price: 현재가
        """
        if symbol in self.positions:
            self.positions[symbol].current_price = current_price
    
    def get_portfolio_value(self) -> float:
        """전체 포트폴리오 가치
        
        Returns:
            float: 현금 + 모든 포지션의 시장 가치
        """
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
    
    def get_total_pnl(self) -> float:
        """총 손익
        
        Returns:
            float: 현재 포트폴리오 가치 - 초기 자본
        """
        return self.get_portfolio_value() - self.initial_capital
    
    def get_total_pnl_pct(self) -> float:
        """총 손익률 (%)
        
        Returns:
            float: (현재 가치 - 초기 자본) / 초기 자본 * 100
        """
        if self.initial_capital == 0:
            return 0.0
        return (self.get_total_pnl() / self.initial_capital) * 100
