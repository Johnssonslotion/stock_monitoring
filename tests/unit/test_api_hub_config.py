"""
Unit Tests for API Hub v2 Configuration Manager

Tests configuration loading, environment variable overrides,
default values, and typed access patterns.
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.api_gateway.hub.config import HubConfig


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    config_content = """
api_hub:
  worker:
    redis_url: "redis://test:6379/15"
    enable_mock: true
    max_retries: 5
    timeout: 15.0
    batch_size: 200
    shutdown_timeout: 10.0
    
  queues:
    priority: "test:priority:queue"
    normal: "test:request:queue"
    response_ttl: 7200
    max_queue_size: 20000
    
  circuit_breaker:
    failure_threshold: 10
    recovery_timeout: 60.0
    half_open_max_calls: 5
    success_threshold: 3
    
  providers:
    KIS:
      enabled: true
      base_url: "https://test-kis.example.com"
      timeout: 20.0
      rate_limit:
        requests_per_second: 30
        burst: 10
        window: 1.0
      retry:
        max_attempts: 5
        backoff_factor: 3.0
        
    KIWOOM:
      enabled: true
      base_url: "https://test-kiwoom.example.com"
      timeout: 20.0
      rate_limit:
        requests_per_second: 15
        burst: 5
        window: 1.0
      retry:
        max_attempts: 5
        backoff_factor: 3.0
        
  token_manager:
    redis_key_prefix: "test:token:"
    auto_refresh_margin: 600
    max_refresh_retries: 5
    refresh_backoff_factor: 3.0
    token_ttl_buffer: 120
    
  rate_limiter:
    redis_url: "redis://test-gatekeeper:6379/0"
    enabled: true
    global_limit: 100
    per_provider_limit: true
    algorithm: "token_bucket"
    rejection_ttl: 120
    
  monitoring:
    log_level: "DEBUG"
    metrics_enabled: true
    health_check_interval: 5.0
    alert_on_circuit_open: true
    
  testing:
    mock_latency_ms: 200
    mock_failure_rate: 0.1
    enable_test_endpoints: true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestHubConfigBasic:
    """Basic configuration loading and access tests"""
    
    def test_load_from_file(self, temp_config_file):
        """Test loading configuration from YAML file"""
        config = HubConfig(config_path=temp_config_file)
        
        assert config.get("worker.redis_url") == "redis://test:6379/15"
        assert config.get("worker.enable_mock") is True
        assert config.get("worker.max_retries") == 5
        assert config.get("worker.timeout") == 15.0
    
    def test_default_values_when_file_not_found(self):
        """Test default values are used when config file doesn't exist"""
        config = HubConfig(config_path="/nonexistent/path.yaml")
        
        # Should have default values from _get_defaults()
        assert config.get("worker.redis_url") is not None
        assert isinstance(config.get("worker.enable_mock"), bool)
        assert config.get("worker.max_retries") == 3  # Default value
    
    def test_dot_notation_access(self, temp_config_file):
        """Test dot notation access to nested config values"""
        config = HubConfig(config_path=temp_config_file)
        
        # Test various nesting levels
        assert config.get("worker.redis_url") == "redis://test:6379/15"
        assert config.get("queues.priority") == "test:priority:queue"
        assert config.get("circuit_breaker.failure_threshold") == 10
        assert config.get("monitoring.log_level") == "DEBUG"
    
    def test_default_parameter(self, temp_config_file):
        """Test default parameter when key doesn't exist"""
        config = HubConfig(config_path=temp_config_file)
        
        # Non-existent key should return default
        assert config.get("nonexistent.key", default="fallback") == "fallback"
        assert config.get("worker.nonexistent", default=999) == 999


class TestHubConfigEnvironmentOverrides:
    """Test environment variable override behavior"""
    
    def test_redis_url_override(self, temp_config_file):
        """Test REDIS_URL environment variable overrides config file"""
        with patch.dict(os.environ, {"REDIS_URL": "redis://env-override:6379/10"}):
            config = HubConfig(config_path=temp_config_file)
            assert config.get("worker.redis_url") == "redis://env-override:6379/10"
    
    def test_enable_mock_override(self, temp_config_file):
        """Test ENABLE_MOCK environment variable overrides config file"""
        with patch.dict(os.environ, {"ENABLE_MOCK": "false"}):
            config = HubConfig(config_path=temp_config_file)
            assert config.get("worker.enable_mock") is False
        
        with patch.dict(os.environ, {"ENABLE_MOCK": "true"}):
            config = HubConfig(config_path=temp_config_file)
            assert config.get("worker.enable_mock") is True
    
    def test_provider_url_override(self, temp_config_file):
        """Test provider URL environment variable overrides"""
        with patch.dict(os.environ, {
            "KIS_BASE_URL": "https://env-kis.example.com",
            "KIWOOM_API_URL": "https://env-kiwoom.example.com"
        }):
            config = HubConfig(config_path=temp_config_file)
            
            kis_config = config.get_provider_config("KIS")
            assert kis_config["base_url"] == "https://env-kis.example.com"
            
            kiwoom_config = config.get_provider_config("KIWOOM")
            assert kiwoom_config["base_url"] == "https://env-kiwoom.example.com"
    
    def test_rate_limiter_url_override(self, temp_config_file):
        """Test RATE_LIMITER_URL environment variable override"""
        with patch.dict(os.environ, {"RATE_LIMITER_URL": "redis://env-limiter:6379/5"}):
            config = HubConfig(config_path=temp_config_file)
            assert config.get("rate_limiter.redis_url") == "redis://env-limiter:6379/5"
    
    def test_log_level_override(self, temp_config_file):
        """Test LOG_LEVEL environment variable override"""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            config = HubConfig(config_path=temp_config_file)
            assert config.get("monitoring.log_level") == "ERROR"


class TestHubConfigHelperMethods:
    """Test helper methods for common config access patterns"""
    
    def test_is_mock_enabled(self, temp_config_file):
        """Test is_mock_enabled() helper method"""
        config = HubConfig(config_path=temp_config_file)
        assert config.is_mock_enabled() is True
        
        with patch.dict(os.environ, {"ENABLE_MOCK": "false"}):
            config = HubConfig(config_path=temp_config_file)
            assert config.is_mock_enabled() is False
    
    def test_get_redis_url(self, temp_config_file):
        """Test get_redis_url() helper method"""
        config = HubConfig(config_path=temp_config_file)
        assert config.get_redis_url() == "redis://test:6379/15"
    
    def test_get_rate_limiter_url(self, temp_config_file):
        """Test get_rate_limiter_url() helper method"""
        config = HubConfig(config_path=temp_config_file)
        assert config.get_rate_limiter_url() == "redis://test-gatekeeper:6379/0"
    
    def test_get_provider_config(self, temp_config_file):
        """Test get_provider_config() helper method"""
        config = HubConfig(config_path=temp_config_file)
        
        # Test KIS provider
        kis_config = config.get_provider_config("KIS")
        assert kis_config is not None
        assert kis_config["enabled"] is True
        assert kis_config["base_url"] == "https://test-kis.example.com"
        assert kis_config["rate_limit"]["requests_per_second"] == 30
        
        # Test KIWOOM provider
        kiwoom_config = config.get_provider_config("KIWOOM")
        assert kiwoom_config is not None
        assert kiwoom_config["enabled"] is True
        assert kiwoom_config["base_url"] == "https://test-kiwoom.example.com"
        
        # Test non-existent provider
        assert config.get_provider_config("NONEXISTENT") is None


class TestHubConfigProviders:
    """Test provider-specific configuration"""
    
    def test_kis_provider_config(self, temp_config_file):
        """Test KIS provider configuration values"""
        config = HubConfig(config_path=temp_config_file)
        kis = config.get_provider_config("KIS")
        
        assert kis["enabled"] is True
        assert kis["base_url"] == "https://test-kis.example.com"
        assert kis["timeout"] == 20.0
        assert kis["rate_limit"]["requests_per_second"] == 30
        assert kis["rate_limit"]["burst"] == 10
        assert kis["retry"]["max_attempts"] == 5
        assert kis["retry"]["backoff_factor"] == 3.0
    
    def test_kiwoom_provider_config(self, temp_config_file):
        """Test KIWOOM provider configuration values"""
        config = HubConfig(config_path=temp_config_file)
        kiwoom = config.get_provider_config("KIWOOM")
        
        assert kiwoom["enabled"] is True
        assert kiwoom["base_url"] == "https://test-kiwoom.example.com"
        assert kiwoom["timeout"] == 20.0
        assert kiwoom["rate_limit"]["requests_per_second"] == 15
        assert kiwoom["rate_limit"]["burst"] == 5
        assert kiwoom["retry"]["max_attempts"] == 5


class TestHubConfigCircuitBreaker:
    """Test circuit breaker configuration"""
    
    def test_circuit_breaker_config(self, temp_config_file):
        """Test circuit breaker configuration values"""
        config = HubConfig(config_path=temp_config_file)
        
        assert config.get("circuit_breaker.failure_threshold") == 10
        assert config.get("circuit_breaker.recovery_timeout") == 60.0
        assert config.get("circuit_breaker.half_open_max_calls") == 5
        assert config.get("circuit_breaker.success_threshold") == 3


class TestHubConfigQueues:
    """Test queue configuration"""
    
    def test_queue_config(self, temp_config_file):
        """Test queue configuration values"""
        config = HubConfig(config_path=temp_config_file)
        
        assert config.get("queues.priority") == "test:priority:queue"
        assert config.get("queues.normal") == "test:request:queue"
        assert config.get("queues.response_ttl") == 7200
        assert config.get("queues.max_queue_size") == 20000


class TestHubConfigTokenManager:
    """Test token manager configuration"""
    
    def test_token_manager_config(self, temp_config_file):
        """Test token manager configuration values"""
        config = HubConfig(config_path=temp_config_file)
        
        assert config.get("token_manager.redis_key_prefix") == "test:token:"
        assert config.get("token_manager.auto_refresh_margin") == 600
        assert config.get("token_manager.max_refresh_retries") == 5
        assert config.get("token_manager.refresh_backoff_factor") == 3.0
        assert config.get("token_manager.token_ttl_buffer") == 120


class TestHubConfigRateLimiter:
    """Test rate limiter configuration"""
    
    def test_rate_limiter_config(self, temp_config_file):
        """Test rate limiter configuration values"""
        config = HubConfig(config_path=temp_config_file)
        
        assert config.get("rate_limiter.redis_url") == "redis://test-gatekeeper:6379/0"
        assert config.get("rate_limiter.enabled") is True
        assert config.get("rate_limiter.global_limit") == 100
        assert config.get("rate_limiter.per_provider_limit") is True
        assert config.get("rate_limiter.algorithm") == "token_bucket"
        assert config.get("rate_limiter.rejection_ttl") == 120


class TestHubConfigMonitoring:
    """Test monitoring configuration"""
    
    def test_monitoring_config(self, temp_config_file):
        """Test monitoring configuration values"""
        config = HubConfig(config_path=temp_config_file)
        
        assert config.get("monitoring.log_level") == "DEBUG"
        assert config.get("monitoring.metrics_enabled") is True
        assert config.get("monitoring.health_check_interval") == 5.0
        assert config.get("monitoring.alert_on_circuit_open") is True


class TestHubConfigTesting:
    """Test testing/development configuration"""
    
    def test_testing_config(self, temp_config_file):
        """Test testing configuration values"""
        config = HubConfig(config_path=temp_config_file)
        
        assert config.get("testing.mock_latency_ms") == 200
        assert config.get("testing.mock_failure_rate") == 0.1
        assert config.get("testing.enable_test_endpoints") is True


class TestHubConfigIntegration:
    """Integration tests with real config file"""
    
    def test_load_actual_config_file(self):
        """Test loading the actual api_hub_v2.yaml config file"""
        config_path = "configs/api_hub_v2.yaml"
        
        if not Path(config_path).exists():
            pytest.skip(f"Config file not found: {config_path}")
        
        config = HubConfig(config_path=config_path)
        
        # Verify key settings exist
        assert config.get("worker.redis_url") is not None
        assert config.get("worker.enable_mock") is not None
        assert config.get("queues.priority") is not None
        assert config.get("circuit_breaker.failure_threshold") is not None
        
        # Verify providers exist
        assert config.get_provider_config("KIS") is not None
        assert config.get_provider_config("KIWOOM") is not None
    
    def test_default_config_when_no_file(self):
        """Test that default config works when no file exists"""
        config = HubConfig(config_path="/nonexistent/config.yaml")
        
        # Should still have working config with defaults
        assert config.get("worker.redis_url") is not None
        assert isinstance(config.get("worker.enable_mock"), bool)
        assert config.get("worker.max_retries") > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
