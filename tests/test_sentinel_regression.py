import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys

# Mock docker before import
mock_docker = MagicMock()
sys.modules["docker"] = mock_docker

from src.monitoring.sentinel import Sentinel

@pytest.mark.asyncio
async def test_sentinel_heartbeat_regression_fix():
    """
    ISSUE-032 Regression Test:
    Ensures that monitor_heartbeat does not crash with TypeError
    when last_restart_time is a datetime object.
    """
    sentinel = Sentinel()
    sentinel.redis = AsyncMock()
    sentinel.is_running = True
    
    # Set last_restart_time to a datetime object (as now set in the code)
    sentinel.last_restart_time = datetime.now() - timedelta(minutes=40)
    
    # Force KR market to be open for the test
    with patch.object(Sentinel, 'is_market_open', return_value=True):
        # We want to trigger the restart logic condition: gap > 300
        # self.last_arrival is empty, so gap will be uptime = (now - startup_time)
        sentinel.startup_time = datetime.now() - timedelta(seconds=350)
        
        # We need check_circuit_breaker to return True
        with patch.object(Sentinel, 'check_circuit_breaker', return_value=True):
            # Run one cycle of monitor_heartbeat
            # Since monitor_heartbeat is an infinite loop, we run it as a task and cancel
            task = asyncio.create_task(sentinel.monitor_heartbeat())
            
            # Wait a bit for the first iteration
            await asyncio.sleep(0.1)
            
            sentinel.is_running = False
            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()
            except Exception as e:
                pytest.fail(f"monitor_heartbeat crashed with {type(e).__name__}: {e}")

@pytest.mark.asyncio
async def test_process_orderbook_updates_heartbeat():
    """
    Verified that process_orderbook updates the market heartbeat,
    addressing pre-market silence alerts.
    """
    sentinel = Sentinel()
    sentinel.last_arrival = {}
    
    orderbook_data = {
        "symbol": "005930",
        "timestamp": datetime.now().isoformat(),
        "source": "KIWOOM"
    }
    
    await sentinel.process_orderbook(orderbook_data)
    
    # Verify both specific and general market arrival times were updated
    assert "KR_ORDERBOOK" in sentinel.last_arrival
    assert "KR" in sentinel.last_arrival
    assert isinstance(sentinel.last_arrival["KR"], datetime)
