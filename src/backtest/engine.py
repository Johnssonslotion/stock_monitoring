"""백테스팅 엔진 (Backtest Engine)

이벤트 기반 백테스팅 엔진으로, 데이터를 전략에 공급하고 매매를 시뮬레이션합니다.
"""
import sys
import os
import asyncio
import logging
import yaml
from datetime import datetime
from typing import List, Dict, Any, Optional

from .data_loader import DataLoader
from .strategies.base import Strategy, Signal, OrderSide
from .metrics import PerformanceMetrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BacktestEngine:
    """백테스팅 엔진 코어"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.backtest_config = self.config['backtest']
        self.strategy_config = self.config['strategy']
        self.risk_config = self.config.get('risk', {})
        self.cost_config = self.config.get('costs', {})
        
        # 환경 변수 우선 사용 (Docker 컨테이너 내부 환경 고려)
        self.data_loader = DataLoader({
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5433)),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'database': os.getenv('DB_NAME', 'backtest_db')
        })
        
        self.strategy: Optional[Strategy] = None
        self.equity_curve = []
        self.trades = []
        self.initial_capital = self.backtest_config['initial_capital']
        self.current_cash = self.initial_capital

    def _init_strategy(self):
        """설정된 전략 클래스 동적 로드"""
        module_name = f"src.backtest.strategies.{self.strategy_config['name']}"
        class_name = self.strategy_config['class_name']
        
        try:
            import importlib
            module = importlib.import_module(module_name)
            strategy_cls = getattr(module, class_name)
            
            # 파라미터 전달하여 인스턴스 생성
            params = self.strategy_config.get('params', {})
            self.strategy = strategy_cls(**params)
            self.strategy.initial_capital = self.initial_capital
            self.strategy.cash = self.initial_capital
            
            logger.info(f"Strategy initialized: {class_name}")
        except Exception as e:
            logger.error(f"Failed to initialize strategy: {e}")
            raise

    async def run(self):
        """백테스트 실행"""
        await self.data_loader.init_db()  # 스키마 초기화 확인
        self._init_strategy()
        
        start_date = datetime.strptime(self.backtest_config['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(self.backtest_config['end_date'], '%Y-%m-%d')
        symbols = self.backtest_config['symbols']
        
        logger.info(f"Starting backtest: {start_date} ~ {end_date} for {symbols}")
        
        total_ticks = await self.data_loader.get_total_tick_count(symbols, start_date, end_date)
        logger.info(f"Total ticks to process: {total_ticks}")
        
        processed_count = 0
        last_log_time = datetime.now()

        async for tick in self.data_loader.fetch_ticks(symbols, start_date, end_date):
            # 1. 전략에 틱 전달
            await self.strategy.on_tick(tick)
            
            # 2. 매매 신호 생성 확인
            signals = self.strategy.generate_signals()
            
            # 3. 신호 처리 (체결 시뮬레이션)
            for signal in signals:
                self._process_signal(signal, tick)
            
            # 4. 자산 현황 기록 (필요 시 매 틱마다 혹은 주기적으로)
            if processed_count % 1000 == 0:
                self.equity_curve.append({
                    'timestamp': tick['timestamp'],
                    'equity': self.strategy.get_portfolio_value()
                })
            
            processed_count += 1
            if (datetime.now() - last_log_time).total_seconds() > 5:
                progress = (processed_count / total_ticks) * 100 if total_ticks > 0 else 0
                logger.info(f"Progress: {progress:.2f}% ({processed_count}/{total_ticks})")
                last_log_time = datetime.now()

        # 종료 시 최종 자산 기록
        self.equity_curve.append({
            'timestamp': end_date,
            'equity': self.strategy.get_portfolio_value()
        })

        logger.info("Backtest complete. Calculating metrics...")
        results = PerformanceMetrics.calculate(self.initial_capital, self.equity_curve, self.trades)
        
        self._report_results(results)
        return results

    def _process_signal(self, signal: Signal, current_tick: dict):
        """매매 신호 처리 및 체결 시뮬레이션"""
        # 간단한 체결 모델: 현재 틱 가격으로 즉시 체결
        fill_price = current_tick['price']
        
        # 슬리피지 및 수수료 반영
        slippage = self.cost_config.get('slippage_rate', 0) * fill_price
        commission = self.cost_config.get('commission_rate', 0) * (fill_price * signal.quantity)
        
        if signal.side == OrderSide.BUY:
            actual_fill_price = fill_price + slippage
            total_cost = (actual_fill_price * signal.quantity) + commission
            
            if self.strategy.cash >= total_cost:
                self.strategy.on_order_filled(signal, actual_fill_price)
                self.trades.append({
                    'timestamp': signal.timestamp,
                    'symbol': signal.symbol,
                    'side': 'BUY',
                    'price': actual_fill_price,
                    'quantity': signal.quantity,
                    'cost': total_cost,
                    'pnl': 0
                })
                logger.debug(f"BUY FILLED: {signal.symbol} @ {actual_fill_price}")
            else:
                logger.warning(f"Insuflficient cash for BUY: {signal.symbol}")
                
        elif signal.side == OrderSide.SELL:
            actual_fill_price = fill_price - slippage
            
            # 포지션 확인
            if signal.symbol in self.strategy.positions:
                pos = self.strategy.positions[signal.symbol]
                pnl = (actual_fill_price - pos.avg_price) * signal.quantity - commission
                
                self.strategy.on_order_filled(signal, actual_fill_price)
                self.trades.append({
                    'timestamp': signal.timestamp,
                    'symbol': signal.symbol,
                    'side': 'SELL',
                    'price': actual_fill_price,
                    'quantity': signal.quantity,
                    'pnl': pnl
                })
                logger.debug(f"SELL FILLED: {signal.symbol} @ {actual_fill_price}, PnL: {pnl}")

    def _report_results(self, results: Dict[str, Any]):
        """결과 요약 출력"""
        print("\n" + "="*40)
        print("📊 BACKTEST RESULT SUMMARY")
        print("="*40)
        print(f"Strategy: {self.strategy_config['class_name']}")
        print(f"Total Return: {results.get('total_return_pct', 0):.2f}%")
        print(f"Max Drawdown: {results.get('mdd_pct', 0):.2f}%")
        print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        print(f"Total Trades: {results.get('total_trades', 0)}")
        print(f"Win Rate:     {results.get('win_rate_pct', 0):.2f}%")
        print(f"Final Equity: {results.get('final_equity', 0):,.0f} KRW")
        print("="*40 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/backtest_config.yaml")
    args = parser.parse_args()
    
    engine = BacktestEngine(args.config)
    asyncio.run(engine.run())
