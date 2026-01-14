"""성과 측정 모듈 (Metrics)

백테스팅 결과를 분석하여 수익률, 변동성, MDD 등 주요 지표를 계산합니다.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

class PerformanceMetrics:
    """백테스팅 성과 측정기"""
    
    @staticmethod
    def calculate(
        initial_capital: float,
        equity_curve: List[Dict[str, Any]],
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """전체 성과 지표 계산
        
        Args:
            initial_capital: 초기 자본
            equity_curve: 자산 변화 이력 [{'timestamp': dt, 'equity': value}, ...]
            trades: 매매 내역 [{'timestamp': dt, 'symbol': s, 'side': side, 'price': p, 'qty': q, 'pnl': pnl}, ...]
            
        Returns:
            Dict: 성과 지표 딕셔너리
        """
        if not equity_curve:
            return {"error": "No equity data available"}

        df_equity = pd.DataFrame(equity_curve)
        df_equity.set_index('timestamp', inplace=True)
        
        # 일별 자산으로 리샘플링 (마지막 값 기준)
        daily_equity = df_equity['equity'].resample('D').last().ffill()
        daily_returns = daily_equity.pct_change().dropna()
        
        total_return = (daily_equity.iloc[-1] - initial_capital) / initial_capital
        
        # MDD 계산
        rolling_max = daily_equity.cummax()
        drawdowns = (daily_equity - rolling_max) / rolling_max
        mdd = drawdowns.min()
        
        # Sharpe Ratio (무위험 수익률 0 가정)
        # 252 거래일 기준 연율화
        if len(daily_returns) > 1:
            sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() != 0 else 0
            volatility = daily_returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
            volatility = 0

        # 매매 통계
        df_trades = pd.DataFrame(trades)
        win_rate = 0
        profit_factor = 0
        total_trades = len(trades)
        
        if not df_trades.empty and 'pnl' in df_trades.columns:
            # 매도(청산) 시점의 PnL을 기준으로 승률 계산
            closed_trades = df_trades[df_trades['pnl'] != 0]
            if not closed_trades.empty:
                winning_trades = closed_trades[closed_trades['pnl'] > 0]
                win_rate = len(winning_trades) / len(closed_trades)
                
                gross_profits = closed_trades[closed_trades['pnl'] > 0]['pnl'].sum()
                gross_losses = abs(closed_trades[closed_trades['pnl'] < 0]['pnl'].sum())
                profit_factor = gross_profits / gross_losses if gross_losses != 0 else float('inf')

        return {
            "total_return_pct": total_return * 100,
            "mdd_pct": mdd * 100,
            "sharpe_ratio": float(sharpe_ratio),
            "volatility_pct": volatility * 100,
            "total_trades": total_trades,
            "win_rate_pct": win_rate * 100,
            "profit_factor": float(profit_factor),
            "start_equity": initial_capital,
            "final_equity": daily_equity.iloc[-1]
        }
