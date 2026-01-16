"""
Conflict Resolution 유틸리티

동일 심볼/시간대에 여러 브로커에서 데이터 도착 시
우선순위에 따라 하나의 데이터를 선택합니다.
"""
from typing import List, Dict, Any
from datetime import datetime


def resolve_conflicting_ticks(
    ticks: List[Dict[str, Any]], 
    strategy: str = "broker_priority",
    priority: List[str] = None
) -> Dict[str, Any]:
    """
    중복 틱 데이터 충돌 해결
    
    Args:
        ticks: 동일 심볼/시간대의 틱 데이터 리스트
        strategy: 해결 전략 ('broker_priority', 'timestamp_first', 'average')
        priority: 브로커 우선순위 리스트 (strategy='broker_priority' 시 필수)
    
    Returns:
        선택된 틱 데이터
    """
    if not ticks:
        return {}
    
    if strategy == "broker_priority":
        if not priority:
            priority = ["kis", "mirae", "kiwoom_re"]  # 기본값
        
        # 우선순위 맵 (낮을수록 높은 우선순위)
        priority_map = {broker: idx for idx, broker in enumerate(priority)}
        
        # 가장 높은 우선순위 브로커의 데이터 선택
        return min(ticks, key=lambda t: priority_map.get(t["broker"], 999))
    
    elif strategy == "timestamp_first":
        # received_time이 가장 빠른 데이터 선택
        return min(ticks, key=lambda t: t["received_time"])
    
    elif strategy == "average":
        # 가격 평균 계산 (통계적 접근)
        avg_price = sum(t["price"] for t in ticks) / len(ticks)
        
        # 평균과 가장 가까운 데이터 선택
        return min(ticks, key=lambda t: abs(t["price"] - avg_price))
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
