import asyncio
import os
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from src.verification.realtime_verifier import RealtimeVerifier, RealtimeConfig
from src.verification.worker import VerificationConsumer, VerificationTask, VerificationStatus

@pytest.mark.asyncio
async def test_realtime_recovery_flow_logic():
    """
    Test the flow from gap detection in RealtimeVerifier to task consumption in VerificationWorker.
    Mocks DB and API to focus on the logic flow and Redis queue interaction.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/9") # Use DB 9
    
    # 1. Setup Verifier
    verifier = RealtimeVerifier(redis_url=redis_url)
    await verifier.initialize()
    
    # Clear previous tasks
    await verifier.redis.delete("verify:queue:priority")
    
    # Mock DB volume: return 100 (log has 100)
    # Mock API volume: return 200 (API has 200) -> Gap detected!
    target_minute = (datetime.now() - timedelta(minutes=1)).replace(second=0, microsecond=0)
    target_str = target_minute.strftime("%Y%m%d%H%M")
    
    verifier._get_tick_volume_from_db = AsyncMock(return_value=100)
    verifier.kiwoom_client.fetch_minute_candle = AsyncMock(return_value=[
        {"dt": target_str, "trde_qty": "200"}
    ])
    
    # 2. Run single verification
    # verify_last_minute will detect 100 vs 200 gap and call _trigger_recovery -> produce_recovery_task
    result = await verifier.verify_last_minute("005930")
    
    assert result.status == VerificationStatus.NEEDS_RECOVERY
    assert result.db_volume == 100
    assert result.kiwoom_volume == 200
    
    # Check if task is in Redis Priority Queue
    queue_len = await verifier.redis.llen("verify:queue:priority")
    assert queue_len == 1
    
    raw_task = await verifier.redis.rpop("verify:queue:priority")
    task = json.loads(raw_task)
    assert task['task_type'] == "recovery"
    assert task['symbol'] == "005930"
    
    # 3. Setup Consumer to handle the task
    consumer = VerificationConsumer(redis_url=redis_url)
    await consumer.connect()
    
    # Mock KIS API for tick recovery
    # Return 3 ticks for the target minute
    mock_ticks = [
        {"stck_cntg_hour": datetime.now().strftime("%H%M") + "01", "stck_prpr": "70000", "cntg_vol": "50"},
        {"stck_cntg_hour": datetime.now().strftime("%H%M") + "30", "stck_prpr": "70100", "cntg_vol": "50"}
    ]
    consumer.kis_client.fetch_tick_data = AsyncMock(return_value=mock_ticks)
    # Mock DB save
    consumer._save_recovered_ticks = AsyncMock(return_value=2)
    
    # Execute recovery handler directly for testing
    task_obj = VerificationTask(**task)
    with patch('aiohttp.ClientSession', autospec=True): # Prevent actual session creation
        rec_result = await consumer._handle_recovery_task(None, task_obj)
    
    assert rec_result.status == VerificationStatus.PASS
    assert "Recovered 2 ticks" in rec_result.message
    
    # Cleanup
    await verifier.cleanup()
    await consumer.close()
    print("\n✅ Real-time recovery flow logic verified!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_realtime_recovery_flow_logic())
