"""
Pillar 8: Market Intelligence & Rotation Analysis

투자자별 수급, 공매도 현황, 프로그램 매매 데이터를 수집하고
섹터 간 순환매를 분석하는 모듈입니다.

RFC: RFC-010
"""

from .investor_trends_collector import InvestorTrendsCollector

__all__ = [
    "InvestorTrendsCollector",
]
