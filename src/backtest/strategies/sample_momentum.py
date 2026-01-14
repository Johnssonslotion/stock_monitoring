"""샘플 모멘텀 전략

단순한 모멘텀 전략으로 백테스팅 엔진 검증용으로 사용됩니다.

전략 로직:
- N일 이동평균 대비 현재가가 threshold 이상 상승 시 매수
- 포지션이 있을 때 stop_loss 이하 하락 시 매도
"""
from datetime import datetime
from typing import List, Dict
from collections import deque

from .base import Strategy, Signal, OrderSide, OrderType


class SampleMomentumStrategy(Strategy):
    """샘플 모멘텀 전략
    
    Args:
        window: 이동평균 윈도우 사이즈 (기본: 20)
        threshold: 매수 임계값, MA 대비 상승률 (기본: 0.02 = 2%)
        stop_loss: 손절 임계값, 매수가 대비 하락률 (기본: 0.05 = 5%)
        position_size: 매수 수량 (기본: 10)
    """
    
    def __init__(
        self,
        window: int = 20,
        threshold: float = 0.02,
        stop_loss: float = 0.05,
        position_size: int = 10
    ):
        super().__init__()
        self.window = window
        self.threshold = threshold
        self.stop_loss = stop_loss
        self.position_size = position_size
        
        # 심볼별 가격 히스토리
        self.price_history: Dict[str, deque] = {}
        
        # 심볼별 최근 틱 데이터
        self.latest_tick: Dict[str, dict] = {}
    
    async def on_tick(self, tick_data: dict):
        """틱 데이터 수신 시 호출"""
        symbol = tick_data['symbol']
        price = tick_data['price']
        
        # 가격 히스토리 초기화
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.window)
        
        # 가격 추가
        self.price_history[symbol].append(price)
        
        # 최근 틱 데이터 저장
        self.latest_tick[symbol] = tick_data
        
        # 포지션 현재가 업데이트
        self.update_position(symbol, price)
    
    def generate_signals(self) -> List[Signal]:
        """매매 신호 생성"""
        signals = []
        
        for symbol, tick_data in self.latest_tick.items():
            # 데이터 부족 시 스킵
            if len(self.price_history[symbol]) < self.window:
                continue
            
            current_price = tick_data['price']
            avg_price = sum(self.price_history[symbol]) / len(self.price_history[symbol])
            
            # 매수 신호: 포지션 없고, 현재가가 MA 대비 threshold 이상 상승
            if symbol not in self.positions:
                if current_price > avg_price * (1 + self.threshold):
                    signals.append(Signal(
                        timestamp=tick_data['timestamp'],
                        symbol=symbol,
                        side=OrderSide.BUY,
                        quantity=self.position_size,
                        order_type=OrderType.MARKET,
                        reason=f"Momentum: {current_price:.2f} > MA({self.window}) {avg_price:.2f}"
                    ))
            
            # 매도 신호: 포지션 있고, 손실이 stop_loss 이상
            elif symbol in self.positions:
                position = self.positions[symbol]
                loss_pct = (current_price - position.avg_price) / position.avg_price
                
                if loss_pct <= -self.stop_loss:
                    signals.append(Signal(
                        timestamp=tick_data['timestamp'],
                        symbol=symbol,
                        side=OrderSide.SELL,
                        quantity=position.quantity,
                        order_type=OrderType.MARKET,
                        reason=f"Stop Loss: {loss_pct*100:.2f}% loss"
                    ))
        
        return signals
    
    def on_order_filled(self, signal: Signal, fill_price: float):
        """주문 체결 시 호출"""
        symbol = signal.symbol
        
        if signal.side == OrderSide.BUY:
            # 매수: 포지션 생성
            from .base import Position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=signal.quantity,
                avg_price=fill_price,
                current_price=fill_price
            )
            # 현금 차감
            total_cost = fill_price * signal.quantity
            self.cash -= total_cost
            
        elif signal.side == OrderSide.SELL:
            # 매도: 포지션 제거
            if symbol in self.positions:
                total_proceeds = fill_price * signal.quantity
                self.cash += total_proceeds
                del self.positions[symbol]
