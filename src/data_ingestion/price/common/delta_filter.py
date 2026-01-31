import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("DeltaFilter")

class OrderbookDeltaFilter:
    """
    호가 데이터의 변경 사항을 추적하여 중복 저장을 방지하는 필터
    """
    def __init__(self):
        # symbol -> last_seen_data (prices and volumes only)
        self._last_state: Dict[str, Dict[str, Any]] = {}

    def should_publish(self, symbol: str, current_data: Dict[str, Any]) -> bool:
        """
        이전 데이터와 비교하여 변경 사항이 있는지 확인
        
        Args:
            symbol (str): 종목 코드
            current_data (dict): 현재 호가 데이터 (KiwoomOrderbookData.model_dump() 결과물)
            
        Returns:
            bool: 변경되었으면 True, 동일하면 False
        """
        # 비교 대상 필드 추출 (가격 및 잔량 리스트)
        state_keys = ['ask_prices', 'bid_prices', 'ask_volumes', 'bid_volumes']
        current_state = {k: current_data.get(k) for k in state_keys}

        if symbol not in self._last_state:
            self._last_state[symbol] = current_state
            return True

        # 이전 상태와 비교 (리스트 값 비교)
        if self._last_state[symbol] == current_state:
            return False

        # 상태 업데이트 및 발행 허가
        self._last_state[symbol] = current_state
        return True

    def reset(self, symbol: Optional[str] = None):
        """특정 종목 또는 전체 상태 초기화"""
        if symbol:
            self._last_state.pop(symbol, None)
        else:
            self._last_state.clear()
