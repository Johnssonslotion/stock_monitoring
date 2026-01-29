import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.verification.worker import VerificationConsumer, VerificationResult, VerificationStatus, VerificationTask, ConfidenceLevel

# Mock Classes
class MockAPIHubClient:
    def __init__(self):
        self.execute = AsyncMock()
    async def close(self): pass

@pytest.mark.asyncio
async def test_verification_fallback_tick_failure():
    """
    Scenario:
    1. DB Integrity Check detected a gap (Mocked DB fetch says 0 vol).
    2. API Candle fetch returns valid candle (Mocked API).
    3. Tick Recovery Attempt Fails (Mocked Tick API error).
    4. Fallback: Candle Upsert triggered and succeeds.
    5. Result Status should be TICKS_UNAVAILABLE.
    """
    consumer = VerificationConsumer()
    consumer.hub_client = MockAPIHubClient()
    consumer.db_pool = MagicMock() # Mock Pool
    consumer.db_pool.acquire.return_value.__aenter__.return_value.fetchrow = AsyncMock(return_value={'vol': 0})
    consumer.db_pool.acquire.return_value.__aenter__.return_value.executemany = AsyncMock()

    # Mock DB View Fetch (return 0 volume to simulate missing data)
    
    # Mock API Candle Fetch (Valid Data)
    consumer.hub_client.execute.side_effect = [
        # 1. Minute Candle Fetch (Success)
        {
            "status": "SUCCESS",
            "data": {
                "output2": [
                    {
                        "stck_cntg_hour": "100000",
                        "stck_oprc": "60000", "stck_hgpr": "60100",
                        "stck_lwpr": "59900", "stck_prpr": "60000",
                        "cntg_vol": "100"
                    }
                ]
            }
        },
        # 2. Tick Data Fetch (Fail)
        { "status": "FAIL", "reason": "Connection Error" } 
    ]
    
    # Task
    task = VerificationTask(
        task_type="verify_db_integrity",
        symbol="005930",
        minute="2026-01-20T10:00:00"
    )

    # Run
    result = await consumer._handle_db_integrity_task(task)

    # Assertions
    assert result.status == VerificationStatus.TICKS_UNAVAILABLE
    assert "Recovered via Candle Fallback" in result.message
    
    # Verify Upsert Called
    consumer.db_pool.acquire.return_value.__aenter__.return_value.executemany.assert_called_once()
    args = consumer.db_pool.acquire.return_value.__aenter__.return_value.executemany.call_args[0][1]
    assert len(args) == 1
    assert args[0][1] == "005930" # Symbol
    assert args[0][6] == 100 # Volume

@pytest.mark.asyncio
async def test_verification_tick_recovery_success():
    """
    Scenario:
    1. Tick Recovery Attempt Succeeds.
    2. Result Status should be PASS (Recovered via Ticks).
    """
    consumer = VerificationConsumer()
    consumer.hub_client = MockAPIHubClient()
    consumer.db_pool = MagicMock()
    consumer.db_pool.acquire.return_value.__aenter__.return_value.fetchrow = AsyncMock(return_value={'vol': 0})
    consumer._refresh_continuous_aggregates = AsyncMock()
    consumer._save_recovered_ticks = AsyncMock(return_value=50) # Mock 50 ticks saved

    # Mock API Responses
    consumer.hub_client.execute.side_effect = [
        # 1. Minute Candle (Gap detected logic uses this? No, only for comparison)
        # Actually _handle_db_integrity_task calls _fetch_api_candles_range first.
        {
            "status": "SUCCESS",
            "data": {"output2": [{"stck_cntg_hour": "100000", "cntg_vol": "100"}]}
        },
        # 2. Tick Fetch (Success)
        {
            "status": "SUCCESS",
            "data": {"output1": [{"stck_cntg_hour": "100000"}]} # Mock item
        }
    ]

    task = VerificationTask(task_type="verify_db_integrity", symbol="005930", minute="2026-01-20T10:00:00")
    
    result = await consumer._handle_db_integrity_task(task)
    
    assert result.status == VerificationStatus.PASS
    assert "Recovered via Ticks" in result.message

@pytest.mark.asyncio
async def test_verification_batch_day():
    """
    Scenario:
    1. Batch Task (Date provided).
    2. Logic should calculate start/end time for the whole day (09:00-15:30).
    3. Mock API returns volume mismatch.
    4. Recovery should be triggered (Tick Recovery simulated).
    """
    consumer = VerificationConsumer()
    consumer.hub_client = MockAPIHubClient()
    consumer.db_pool = MagicMock()
    consumer.db_pool.acquire.return_value.__aenter__.return_value.fetchrow = AsyncMock(return_value={'vol': 1000}) # DB low volume
    consumer._refresh_continuous_aggregates = AsyncMock()
    consumer._save_recovered_ticks = AsyncMock(return_value=500) 

    # Mock API Responses
    consumer.hub_client.execute.side_effect = [
        # 1. Minute Candle Fetch (Returns valid high volume)
        {
            "status": "SUCCESS",
            "data": {"output2": [{"stck_cntg_hour": "100000", "cntg_vol": "2000"}]} # Gap 100%
        },
        # 2. Tick Fetch (Success)
        {
            "status": "SUCCESS",
            "data": {"output1": [{"stck_cntg_hour": "100000"}]} 
        }
    ]

    task = VerificationTask(task_type="verify_db_integrity", symbol="005930", date="20260120")
    
    result = await consumer._handle_db_integrity_task(task)
    
    assert result.status == VerificationStatus.TICKS_UNAVAILABLE
    assert "Recovered via Candle Fallback" in result.message
    assert "Batch" in result.message or result.minute is not None # Logic sets minute to start time
