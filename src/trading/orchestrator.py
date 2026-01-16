import asyncio
import logging
import yaml
from typing import Dict, List, Any, Type, Optional
from pathlib import Path
from src.trading.broker_base import BrokerBase
from src.trading.adapters.mirae import MiraeAdapter
from src.trading.adapters.kiwoom_re import KiwoomREAdapter

logger = logging.getLogger(__name__)

class BrokerOrchestrator:
    """
    여러 브로커 워커를 가변적으로 관리하는 오케스트레이터
    """
    ADAPTER_MAP: Dict[str, Type[BrokerBase]] = {
        "mirae": MiraeAdapter,
        "kiwoom_re": KiwoomREAdapter
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_brokers: Dict[str, BrokerBase] = {}
        self.tasks: List[asyncio.Task] = []
        self.symbol_assignments: Dict[str, List[str]] = {}  # broker -> symbols
        self.failover_config: Dict[str, Any] = {}
        self.backup_mappings: Dict[str, str] = {}  # primary -> backup

    def setup_brokers(self, broker_names: List[str]):
        """설정에 따라 브로커 인스턴스 생성"""
        for name in broker_names:
            if name in self.ADAPTER_MAP:
                adapter_cls = self.ADAPTER_MAP[name]
                # 브로커별 개별 설정 추출 (없으면 기본값)
                broker_config = self.config.get("brokers", {}).get(name, {})
                broker_config.update({
                    "redis_url": self.config.get("redis_url"),
                    "use_mock": self.config.get("use_mock", False)
                })
                
                self.active_brokers[name] = adapter_cls(broker_config)
                logger.info(f"🆕 Broker Setup: {name}")
            else:
                logger.warning(f"⚠️ Unknown broker requested: {name}")

    async def start_all(self, symbols: Dict[str, List[str]]):
        """본격적인 수집 및 워커 루프 시작"""
        if not self.active_brokers:
            logger.error("❌ No active brokers to start")
            return

        for name, broker in self.active_brokers.items():
            # 1. Connect
            if await broker.connect():
                # 2. Start Realtime Subscription
                broker_symbols = symbols.get(name, [])
                if await broker.start_realtime_subscribe(broker_symbols):
                    # 3. Add to Task list
                    self.tasks.append(asyncio.create_task(broker.run()))
                    logger.info(f"✅ Broker {name} is running")
            else:
                logger.error(f"❌ Failed to connect broker: {name}")

    async def stop_all(self):
        """모든 워커 중지"""
        for name, broker in self.active_brokers.items():
            broker.is_running = False
            await broker.disconnect()
        
        for task in self.tasks:
            task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("🛑 All brokers stopped")
    
    def load_collection_strategy(self, strategy_path: str = "configs/collection_strategy.yaml"):
        """
        Collection Strategy 설정 파일 로드 및 파싱
        
        Args:
            strategy_path: 설정 파일 경로
        """
        try:
            with open(strategy_path, 'r') as f:
                strategy = yaml.safe_load(f)
            
            logger.info(f"📋 Loading collection strategy: {strategy.get('strategy')}")
            
            # Tier별 심볼 할당
            for tier_name, tier_config in strategy.get('tiers', {}).items():
                symbols = tier_config.get('symbols', [])
                brokers_config = tier_config.get('brokers', {})
                
                primary = brokers_config.get('primary')
                if primary:
                    self.assign_symbols(primary, symbols)
                
                # Failover 설정
                backup = brokers_config.get('backup')
                if backup:
                    delay = brokers_config.get('backup_delay', 0)
                    self.setup_failover(primary, backup, symbols, delay)
            
            # Failover 전역 설정 저장
            self.failover_config = strategy.get('failover', {})
            
            logger.info(f"✅ Collection strategy loaded: {len(self.symbol_assignments)} brokers configured")
            
        except FileNotFoundError:
            logger.error(f"❌ Collection strategy file not found: {strategy_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load collection strategy: {e}")
    
    def assign_symbols(self, broker: str, symbols: List[str]):
        """
        특정 브로커에 심볼 할당
        
        Args:
            broker: 브로커 이름
            symbols: 할당할 심볼 리스트
        """
        if broker not in self.symbol_assignments:
            self.symbol_assignments[broker] = []
        
        # 중복 제거하며 추가
        for symbol in symbols:
            if symbol not in self.symbol_assignments[broker]:
                self.symbol_assignments[broker].append(symbol)
        
        logger.info(f"📌 Assigned {len(symbols)} symbols to {broker}")
    
    def setup_failover(self, primary: str, backup: str, symbols: List[str], delay: int = 0):
        """
        Failover 관계 설정
        
        Args:
            primary: Primary 브로커
            backup: Backup 브로커
            symbols: Failover 대상 심볼
            delay: Backup 활성화 지연 시간 (초)
        """
        self.backup_mappings[primary] = backup
        
        logger.info(f"🔄 Failover configured: {primary} -> {backup} (delay: {delay}s)")
    
    async def activate_backup(self, backup_broker: str, symbols: List[str]):
        """
        Backup 브로커 긴급 활성화
        
        Args:
            backup_broker: 활성화할 Backup 브로커
            symbols: 구독할 심볼
        """
        if backup_broker not in self.active_brokers:
            logger.error(f"❌ Backup broker not found: {backup_broker}")
            return
        
        broker = self.active_brokers[backup_broker]
        
        logger.warning(f"🚨 Activating backup broker: {backup_broker}")
        
        if not broker.is_running:
            # 브로커 연결 및 시작
            if await broker.connect():
                if await broker.start_realtime_subscribe(symbols):
                    task = asyncio.create_task(broker.run())
                    self.tasks.append(task)
                    logger.info(f"✅ Backup broker {backup_broker} activated")
        else:
            # 이미 실행 중이면 추가 심볼만 구독
            await broker.start_realtime_subscribe(symbols)
            logger.info(f"✅ Added symbols to running backup broker {backup_broker}")
