import pytest
import os
from src.core.config import AppConfig

def test_load_config():
    # Ensure the config file exists
    assert os.path.exists("configs/base.yaml")
    
    # Load config
    config = AppConfig.load("configs/base.yaml")
    
    # Verify values
    assert config.project_name == "stock_monitoring"
    assert config.environment == "development"
    assert config.data.base_dir == "data"
    assert "KRW-BTC" in config.exchange.symbols
    assert config.logging.level == "INFO"

def test_missing_config():
    with pytest.raises(FileNotFoundError):
        AppConfig.load("configs/non_existent.yaml")

def test_invalid_config_type():
    """잘못된 타입의 설정값이 들어왔을 때 ValidationError가 발생하는지 테스트"""
    # 임시로 잘못된 YAML 파일 생성
    with open("configs/invalid.yaml", "w") as f:
        f.write("""
project_name: "stock_monitoring"
environment: "development"
data:
  base_dir: "data"
  tick_path: "data/ticks"
  redis_url: "redis://localhost:6379/0"
exchange:
  name: "upbit"
  symbols: "NOT_A_LIST"  # 리스트여야 하는데 문자열이 옴
logging:
  level: "INFO"
  format: "log"
""")
    
    try:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AppConfig.load("configs/invalid.yaml")
    finally:
        if os.path.exists("configs/invalid.yaml"):
            os.remove("configs/invalid.yaml")
