"""
Cost Calculator Module
Responsible for calculating taxes, commissions, and financing costs for virtual trading.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass
class CostConfig:
    """비용 설정 데이터 클래스"""
    broker_name: str = "KIWOOM"
    commission_rate: Decimal = Decimal("0.00015")  # 0.015%
    tax_rate: Decimal = Decimal("0.0018")         # 0.18% (KR Stock Sales)
    currency: str = "KRW"

class CostCalculator:
    """비용 계산기"""
    
    def __init__(self, config: CostConfig):
        self.config = config

    def calculate_commission(self, price: Decimal, quantity: int) -> Decimal:
        """수수료 계산 (매수/매도 공통)"""
        amount = price * quantity
        return amount * self.config.commission_rate

    def calculate_tax(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """세금 계산 (매도 시에만 적용)"""
        if side.upper() != "SELL":
            return Decimal("0")
            
        amount = price * quantity
        return amount * self.config.tax_rate

    def calculate_total_cost(self, price: Decimal, quantity: int, side: str) -> dict:
        """총 비용 계산"""
        price_dec = Decimal(str(price))
        
        commission = self.calculate_commission(price_dec, quantity)
        tax = self.calculate_tax(price_dec, quantity, side)
        
        return {
            "commission": commission,
            "tax": tax,
            "total": commission + tax
        }
