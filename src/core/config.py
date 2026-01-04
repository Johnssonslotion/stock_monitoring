import yaml
import os
from pydantic import BaseModel, Field
from typing import List

class DataConfig(BaseModel):
    base_dir: str = Field(default="data")
    tick_path: str = Field(default="data/ticks")
    redis_url: str = Field(default="redis://localhost:6379/0")

class ExchangeConfig(BaseModel):
    name: str
    symbols: List[str]

class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str

class AppConfig(BaseModel):
    project_name: str
    environment: str
    data: DataConfig
    exchange: ExchangeConfig
    logging: LoggingConfig

    @classmethod
    def load(cls, config_path: str = "configs/base.yaml") -> "AppConfig":
        """
        YAML 파일에서 설정을 로드합니다.
        
        Args:
            config_path (str): YAML 설정 파일의 경로.
            
        Returns:
            AppConfig: 검증된 설정 객체.
            
        Raises:
            FileNotFoundError: 설정 파일이 존재하지 않을 경우.
            ValueError: 설정 값이 유효하지 않을 경우 (Pydantic Validation).
        """
        if not os.path.exists(config_path):
            # Fallback to absolute path relative to project root if needed
            # Assuming running from root
            raise FileNotFoundError(f"Config file not found at {config_path}")
            
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        
        # Override with environment variables if present (Docker/production)
        if "REDIS_URL" in os.environ:
            if "data" not in config_dict:
                config_dict["data"] = {}
            config_dict["data"]["redis_url"] = os.environ["REDIS_URL"]
            
        return cls(**config_dict)

# Singleton instance for easy access
# Usage: from src.core.config import settings
try:
    settings = AppConfig.load()
except FileNotFoundError:
    # Allow import without config file existing (e.g. during specialized tests)
    settings = None
