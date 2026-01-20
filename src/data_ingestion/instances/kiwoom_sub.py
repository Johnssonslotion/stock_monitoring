"""
[RFC-007] Kiwoom Service Entry Point
Dedicated Sub Collector for KR Tick Data (Recovery Source)
"""
import asyncio
import logging
import os
import yaml
from pathlib import Path

from src.data_ingestion.price.kr.kiwoom_ws import KiwoomWSCollector

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Kiwoom-Service")

# Environment Variables
# Kiwoom uses a different set of keys if available, or fallbacks.
# But typically for 'real-collector' we had backups.
# Now we use primary KIWOOM keys from env.
KIWOOM_APP_KEY = os.getenv("KIWOOM_APP_KEY")
KIWOOM_APP_SECRET = os.getenv("KIWOOM_APP_SECRET")
CONFIG_FILE = os.getenv("CONFIG_FILE", "configs/kr_symbols.yaml")

# Explicit Core ETF List (matches kiwoom_ws.py's old CORE_ETFS)
CORE_ETFS = {"122630", "252670", "114800", "069500"}

def load_symbol_configs():
    """Load symbols and determine their subscription types based on group"""
    try:
        config_path = Path(CONFIG_FILE)
        if not config_path.exists():
            config_path = Path("/app") / CONFIG_FILE
            
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        symbol_configs = {}
        symbols_data = config.get('symbols', {})
        
        # 1. Helper to add symbols by group
        def add_from_list(items):
            for item in items:
                sym = item['symbol']
                group = item.get('group', 'rotation')
                # Strategy: Core = Orderbook Only, Rotation = Tick + Orderbook
                if group == 'core' or sym in CORE_ETFS:
                    symbol_configs[sym] = ["0D"]
                else:
                    symbol_configs[sym] = ["0B", "0D"]

        # 2. Process all categories
        add_from_list(symbols_data.get('indices', []))
        add_from_list(symbols_data.get('leverage', []))
        
        for sector in symbols_data.get('sectors', {}).values():
            group = sector.get('group', 'rotation')
            
            # ETF
            if 'etf' in sector:
                sym = sector['etf']['symbol']
                if group == 'core' or sym in CORE_ETFS:
                    symbol_configs[sym] = ["0D"]
                else:
                    symbol_configs[sym] = ["0B", "0D"]
            
            # Stocks
            for stock in sector.get('top3', []):
                sym = stock['symbol']
                # Individual stock group takes priority if exists, else sector group
                s_group = stock.get('group', group)
                if s_group == 'core' or sym in CORE_ETFS:
                    symbol_configs[sym] = ["0D"]
                else:
                    symbol_configs[sym] = ["0B", "0D"]
                
        return symbol_configs
        
    except Exception as e:
        logger.error(f"Failed to load symbol configs: {e}")
        return {}

async def main():
    logger.info("🚀 Starting Kiwoom Service (RFC-007 Isolated)...")
    
    if not KIWOOM_APP_KEY or not KIWOOM_APP_SECRET:
        logger.error("❌ MISSING KIWOOM API KEYS. Exiting.")
        return

    # 1. Load Symbols with Configs
    symbol_configs = load_symbol_configs()
    logger.info(f"Target Symbols: {len(symbol_configs)}")
    
    # Check mock mode
    mock_mode = os.getenv("KIWOOM_MOCK", "False").lower() == "true"
    logger.info(f"🔧 Mock Mode: {mock_mode}")
    
    # 2. Init Collector
    collector = KiwoomWSCollector(
        app_key=KIWOOM_APP_KEY,
        app_secret=KIWOOM_APP_SECRET,
        symbol_configs=symbol_configs,
        mock_mode=mock_mode
    )
    
    # 3. Start
    # Loop is handled inside start() usually, but KiwoomWSCollector.start() is async
    # and might contain the loop. Let's check implementation. 
    # Yes, it has 'while self.running'.
    await collector.start()

if __name__ == "__main__":
    asyncio.run(main())
