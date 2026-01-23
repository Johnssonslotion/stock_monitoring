"""
API Hub v2 Configuration Manager

This module provides configuration management for the API Hub v2 system,
including worker settings, queue configuration, circuit breaker, rate limiting,
and provider-specific settings.

Usage:
    from src.api_gateway.hub.config import hub_config

    # Access config values
    redis_url = hub_config.get("worker.redis_url")
    enable_mock = hub_config.get("worker.enable_mock", default=True)

    # Or use typed access
    worker_config = hub_config.config["api_hub"]["worker"]
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


# Pydantic Models for Type Safety

class WorkerConfig(BaseModel):
    """Worker configuration"""
    redis_url: str = Field(default="redis://localhost:6379/15")
    enable_mock: bool = Field(default=True)
    max_retries: int = Field(default=3)
    timeout: float = Field(default=10.0)
    batch_size: int = Field(default=100)
    shutdown_timeout: float = Field(default=5.0)


class QueueConfig(BaseModel):
    """Queue configuration"""
    priority: str = Field(default="api:priority:queue")
    normal: str = Field(default="api:request:queue")
    response_ttl: int = Field(default=3600)
    max_queue_size: int = Field(default=10000)


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration"""
    failure_threshold: int = Field(default=5)
    recovery_timeout: float = Field(default=30.0)
    half_open_max_calls: int = Field(default=3)
    success_threshold: int = Field(default=2)


class RateLimitConfig(BaseModel):
    """Rate limit configuration for a provider"""
    requests_per_second: int
    burst: int
    window: float = Field(default=1.0)


class RetryConfig(BaseModel):
    """Retry configuration for a provider"""
    max_attempts: int = Field(default=3)
    backoff_factor: float = Field(default=2.0)


class ProviderConfig(BaseModel):
    """Provider-specific configuration"""
    enabled: bool
    base_url: str
    timeout: float = Field(default=10.0)
    rate_limit: RateLimitConfig
    retry: RetryConfig


class TokenManagerConfig(BaseModel):
    """Token manager configuration"""
    redis_key_prefix: str = Field(default="api:token:")
    auto_refresh_margin: int = Field(default=300)
    max_refresh_retries: int = Field(default=3)
    refresh_backoff_factor: float = Field(default=2.0)
    token_ttl_buffer: int = Field(default=60)


class RateLimiterConfig(BaseModel):
    """Rate limiter integration configuration"""
    redis_url: str = Field(default="redis://redis-gatekeeper:6379/0")
    enabled: bool = Field(default=True)
    global_limit: int = Field(default=50)
    per_provider_limit: bool = Field(default=True)
    algorithm: str = Field(default="sliding_window")
    rejection_ttl: int = Field(default=60)


class MonitoringConfig(BaseModel):
    """Monitoring and logging configuration"""
    log_level: str = Field(default="INFO")
    metrics_enabled: bool = Field(default=True)
    health_check_interval: float = Field(default=10.0)
    alert_on_circuit_open: bool = Field(default=True)


class TestingConfig(BaseModel):
    """Testing and development configuration"""
    mock_latency_ms: int = Field(default=100)
    mock_failure_rate: float = Field(default=0.0)
    enable_test_endpoints: bool = Field(default=False)


class ApiHubConfig(BaseModel):
    """Main API Hub configuration"""
    worker: WorkerConfig
    queues: QueueConfig
    circuit_breaker: CircuitBreakerConfig
    providers: Dict[str, ProviderConfig]
    token_manager: TokenManagerConfig
    rate_limiter: RateLimiterConfig
    monitoring: MonitoringConfig
    testing: TestingConfig


# Configuration Manager

class HubConfig:
    """
    API Hub v2 Configuration Manager

    Loads configuration from YAML file and provides typed access
    to configuration values with environment variable overrides.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file. If None, uses default path or env var.
        """
        if config_path is None:
            config_path = os.getenv("HUB_CONFIG_PATH", "configs/api_hub_v2.yaml")

        self.config_path = Path(config_path)
        self.raw_config = self._load_yaml()
        self.config = self._apply_env_overrides(self.raw_config)

        # Validate and create typed config
        try:
            self.typed_config = ApiHubConfig(**self.config["api_hub"])
        except Exception as e:
            # If validation fails, log warning but allow runtime to continue
            # with raw config access
            import logging
            logger = logging.getLogger("HubConfig")
            logger.warning(f"Config validation failed: {e}. Using raw config.")
            self.typed_config = None

    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not self.config_path.exists():
            # Return defaults if config file not found
            return self._get_defaults()

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                return self._get_defaults()
            return config

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            "api_hub": {
                "worker": {
                    "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/15"),
                    "enable_mock": os.getenv("ENABLE_MOCK", "true").lower() == "true",
                    "max_retries": int(os.getenv("HUB_MAX_RETRIES", "3")),
                    "timeout": float(os.getenv("HUB_TIMEOUT", "10.0")),
                    "batch_size": int(os.getenv("HUB_BATCH_SIZE", "100")),
                    "shutdown_timeout": float(os.getenv("HUB_SHUTDOWN_TIMEOUT", "5.0"))
                },
                "queues": {
                    "priority": os.getenv("HUB_PRIORITY_QUEUE", "api:priority:queue"),
                    "normal": os.getenv("HUB_NORMAL_QUEUE", "api:request:queue"),
                    "response_ttl": int(os.getenv("HUB_RESPONSE_TTL", "3600")),
                    "max_queue_size": int(os.getenv("HUB_MAX_QUEUE_SIZE", "10000"))
                },
                "circuit_breaker": {
                    "failure_threshold": int(os.getenv("HUB_CB_FAILURE_THRESHOLD", "5")),
                    "recovery_timeout": float(os.getenv("HUB_CB_RECOVERY_TIMEOUT", "30.0")),
                    "half_open_max_calls": int(os.getenv("HUB_CB_HALF_OPEN_MAX", "3")),
                    "success_threshold": int(os.getenv("HUB_CB_SUCCESS_THRESHOLD", "2"))
                },
                "providers": {},
                "token_manager": {
                    "redis_key_prefix": os.getenv("HUB_TOKEN_PREFIX", "api:token:"),
                    "auto_refresh_margin": int(os.getenv("HUB_TOKEN_REFRESH_MARGIN", "300")),
                    "max_refresh_retries": int(os.getenv("HUB_TOKEN_MAX_RETRIES", "3")),
                    "refresh_backoff_factor": float(os.getenv("HUB_TOKEN_BACKOFF", "2.0")),
                    "token_ttl_buffer": int(os.getenv("HUB_TOKEN_TTL_BUFFER", "60"))
                },
                "rate_limiter": {
                    "redis_url": os.getenv("RATE_LIMITER_URL", "redis://redis-gatekeeper:6379/0"),
                    "enabled": os.getenv("HUB_RATE_LIMITER_ENABLED", "true").lower() == "true",
                    "global_limit": int(os.getenv("HUB_GLOBAL_RATE_LIMIT", "50")),
                    "per_provider_limit": os.getenv("HUB_PER_PROVIDER_LIMIT", "true").lower() == "true",
                    "algorithm": os.getenv("HUB_RATE_LIMIT_ALGORITHM", "sliding_window"),
                    "rejection_ttl": int(os.getenv("HUB_REJECTION_TTL", "60"))
                },
                "monitoring": {
                    "log_level": os.getenv("LOG_LEVEL", "INFO"),
                    "metrics_enabled": os.getenv("HUB_METRICS_ENABLED", "true").lower() == "true",
                    "health_check_interval": float(os.getenv("HUB_HEALTH_CHECK_INTERVAL", "10.0")),
                    "alert_on_circuit_open": os.getenv("HUB_ALERT_ON_CB_OPEN", "true").lower() == "true"
                },
                "testing": {
                    "mock_latency_ms": int(os.getenv("HUB_MOCK_LATENCY_MS", "100")),
                    "mock_failure_rate": float(os.getenv("HUB_MOCK_FAILURE_RATE", "0.0")),
                    "enable_test_endpoints": os.getenv("HUB_ENABLE_TEST_ENDPOINTS", "false").lower() == "true"
                }
            }
        }

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables take precedence over YAML values.
        """
        if "api_hub" not in config:
            config["api_hub"] = {}

        api_hub = config["api_hub"]

        # Worker overrides
        if "worker" in api_hub:
            worker = api_hub["worker"]
            if "REDIS_URL" in os.environ:
                worker["redis_url"] = os.environ["REDIS_URL"]
            if "ENABLE_MOCK" in os.environ:
                worker["enable_mock"] = os.environ["ENABLE_MOCK"].lower() == "true"
            if "HUB_MAX_RETRIES" in os.environ:
                worker["max_retries"] = int(os.environ["HUB_MAX_RETRIES"])
            if "HUB_TIMEOUT" in os.environ:
                worker["timeout"] = float(os.environ["HUB_TIMEOUT"])
            if "LOG_LEVEL" in os.environ and "monitoring" in api_hub:
                api_hub["monitoring"]["log_level"] = os.environ["LOG_LEVEL"]

        # Provider URL overrides (inject from environment)
        if "providers" in api_hub:
            providers = api_hub["providers"]
            if "KIS" in providers and "KIS_BASE_URL" in os.environ:
                providers["KIS"]["base_url"] = os.environ["KIS_BASE_URL"]
            if "KIWOOM" in providers and "KIWOOM_API_URL" in os.environ:
                providers["KIWOOM"]["base_url"] = os.environ["KIWOOM_API_URL"]

        # Rate limiter override
        if "rate_limiter" in api_hub and "RATE_LIMITER_URL" in os.environ:
            api_hub["rate_limiter"]["redis_url"] = os.environ["RATE_LIMITER_URL"]

        return config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot notation path.

        Args:
            key_path: Dot-separated path (e.g., "worker.redis_url")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> hub_config.get("worker.redis_url")
            "redis://localhost:6379/15"

            >>> hub_config.get("worker.enable_mock", default=True)
            True
        """
        # Always prepend "api_hub" if not present
        if not key_path.startswith("api_hub."):
            key_path = f"api_hub.{key_path}"

        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Provider name (e.g., "KIS", "KIWOOM")

        Returns:
            Provider configuration dict or None if not found
        """
        providers = self.get("providers", {})
        return providers.get(provider_name)

    def is_mock_enabled(self) -> bool:
        """Check if mock mode is enabled"""
        return self.get("worker.enable_mock", default=True)

    def get_redis_url(self) -> str:
        """Get Redis URL for worker"""
        return self.get("worker.redis_url", default="redis://localhost:6379/15")

    def get_rate_limiter_url(self) -> str:
        """Get Rate Limiter Redis URL"""
        return self.get("rate_limiter.redis_url", default="redis://redis-gatekeeper:6379/0")


# Singleton instance for easy access
# Usage: from src.api_gateway.hub.config import hub_config
try:
    hub_config = HubConfig()
except Exception as e:
    # Allow import without config file existing (e.g. during tests)
    import logging
    logger = logging.getLogger("HubConfig")
    logger.warning(f"Failed to load hub config: {e}. Using defaults.")
    hub_config = HubConfig()  # Will use defaults
