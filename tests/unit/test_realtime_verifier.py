import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from src.verification.realtime_verifier import RealtimeVerifier, RealtimeConfig
from src.verification.worker import VerificationStatus, ConfidenceLevel

@pytest.fixture
def mock_verifier():
    config = RealtimeConfig(min_volume_threshold=10)
    verifier = RealtimeVerifier(config=config)
    verifier.redis = AsyncMock()
    verifier.db_pool = AsyncMock()
    verifier.producer = AsyncMock()
    verifier.api_hub_client = AsyncMock()  # Mock API Hub Client
    
    # Mock _save_verification_result to avoid DB call
    verifier._save_verification_result = AsyncMock()
    verifier._trigger_recovery = AsyncMock()
    
    return verifier

@pytest.mark.asyncio
async def test_verify_last_minute_pass(mock_verifier):
    symbol = "005930"
    target_time = datetime(2026, 1, 26, 10, 0, 0)
    
    # Mock DB Candle
    mock_verifier._get_local_candle_from_db = AsyncMock(return_value={
        "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1000
    })
    
    # Mock API Candle
    mock_verifier._extract_minute_candle = MagicMock(return_value={
        "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1000
    })

    # Mock API Hub Response (Result of execute)
    mock_verifier.api_hub_client.execute.return_value = {
        "status": "success",
        "data": [{"dummy": "data"}]
    }

    with patch("src.verification.realtime_verifier.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 26, 10, 1, 5) # 1 min later + 5s
        mock_dt.fromisoformat = datetime.fromisoformat
        
        result = await mock_verifier.verify_last_minute(symbol)
        
        assert result.status == VerificationStatus.PASS
        assert result.price_match is True
        assert result.delta_pct == 0.0
        mock_verifier._trigger_recovery.assert_not_called()
        mock_verifier._save_verification_result.assert_called_once()

@pytest.mark.asyncio
async def test_verify_last_minute_price_mismatch(mock_verifier):
    symbol = "005930"
    
    # Mock DB: Open 100
    mock_verifier._get_local_candle_from_db = AsyncMock(return_value={
        "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1000
    })
    
    # Mock API: Open 101 (Mismatch)
    mock_verifier._extract_minute_candle = MagicMock(return_value={
        "open": 101.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1000
    })

    mock_verifier.api_hub_client.execute.return_value = {"status": "success", "data": []}

    with patch("src.verification.realtime_verifier.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 26, 10, 1, 5)
        
        result = await mock_verifier.verify_last_minute(symbol)
        
        assert result.status == VerificationStatus.NEEDS_RECOVERY
        assert result.price_match is False
        assert result.details["open_diff"] == -1.0
        # Recovery triggered with gap 0 (because volume match)
        mock_verifier._trigger_recovery.assert_called_once()

@pytest.mark.asyncio
async def test_verify_last_minute_volume_mismatch(mock_verifier):
    symbol = "005930"
    
    # Mock DB: Vol 1000
    mock_verifier._get_local_candle_from_db = AsyncMock(return_value={
        "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1000
    })
    
    # Mock API: Vol 1050 (5% diff > 2% tolerance)
    mock_verifier._extract_minute_candle = MagicMock(return_value={
        "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1050
    })

    mock_verifier.api_hub_client.execute.return_value = {"status": "success", "data": []}

    with patch("src.verification.realtime_verifier.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 26, 10, 1, 5)
        
        result = await mock_verifier.verify_last_minute(symbol)
        
        assert result.status == VerificationStatus.NEEDS_RECOVERY
        # Price match is True
        assert result.price_match is True
        
        # Recovery triggered with gap 50
        mock_verifier._trigger_recovery.assert_called_once()
        args = mock_verifier._trigger_recovery.call_args[0]
        assert args[2] == 50 # gap
