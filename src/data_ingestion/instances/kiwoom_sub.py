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

def load_symbols():
    """Load target symbols from config"""
    # Assuming standard config structure
    # We need to resolve path relative to project root since this runs as module
    # or rely on absolute path logic in config loader.
    # Ideally, we read the yaml directly here.
    
    try:
        # Resolve config path relative to workspace root (assuming CWD is root)
        config_path = Path(CONFIG_FILE)
        if not config_path.exists():
            # Fallback for nested exec
            config_path = Path("/app") / CONFIG_FILE
            
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        symbols = []
        # Simple extraction logic (can be refined to match shared logic)
        symbols_data = config.get('symbols', {})
        for cat in ['indices', 'leverage']:
            for item in symbols_data.get(cat, []):
                symbols.append(item['symbol'])
        
        for sector in symbols_data.get('sectors', {}).values():
            if 'etf' in sector: symbols.append(sector['etf']['symbol'])
            for stock in sector.get('top3', []):
                symbols.append(stock['symbol'])
                
        return list(set(symbols))
        
    except Exception as e:
        logger.error(f"Failed to load symbols: {e}")
        return []

async def main():
    logger.info("🚀 Starting Kiwoom Service (RFC-007 Isolated)...")
    
    if not KIWOOM_APP_KEY or not KIWOOM_APP_SECRET:
        logger.error("❌ MISSING KIWOOM API KEYS. Exiting.")
        return

    # 1. Load Symbols
    symbols = load_symbols()
    logger.info(f"Target Symbols: {len(symbols)}")
    
    # Check mock mode
    mock_mode = os.getenv("KIWOOM_MOCK", "False").lower() == "true"
    logger.info(f"🔧 Mock Mode: {mock_mode}")
    
    # 2. Init Collector
    collector = KiwoomWSCollector(
        app_key=KIWOOM_APP_KEY,
        app_secret=KIWOOM_APP_SECRET,
        symbols=symbols,
        mock_mode=mock_mode
    )
    
    # 3. Start
    # Loop is handled inside start() usually, but KiwoomWSCollector.start() is async
    # and might contain the loop. Let's check implementation. 
    # Yes, it has 'while self.running'.
    await collector.start()

if __name__ == "__main__":
    asyncio.run(main())
