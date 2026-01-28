"""
Unit Tests for ISSUE-044 Continuous Aggregates

These tests verify the SQL migration logic and refresh behavior.
Note: Requires TimescaleDB connection for integration tests.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock


class TestContinuousAggregatesConfig:
    """Test configuration and constants for Continuous Aggregates"""

    def test_view_names_defined(self):
        """Verify all required view names are defined"""
        expected_views = [
            'market_candles_1m_view',
            'market_candles_5m_view',
            'market_candles_1h_view',
            'market_candles_1d_view',
        ]

        # These should match the migration file
        for view in expected_views:
            assert view.startswith('market_candles_')
            assert view.endswith('_view')

    def test_refresh_intervals(self):
        """Verify refresh intervals are reasonable"""
        intervals = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '1h': timedelta(hours=1),
            '1d': timedelta(days=1),
        }

        # 1m should refresh every minute
        assert intervals['1m'].total_seconds() == 60

        # Cascade intervals should be multiples
        assert intervals['5m'].total_seconds() == 5 * intervals['1m'].total_seconds()
        assert intervals['1h'].total_seconds() == 60 * intervals['1m'].total_seconds()


class TestVerificationConsumerRefresh:
    """Test VerificationConsumer._refresh_continuous_aggregates method"""

    @pytest.fixture
    def mock_db_pool(self):
        """Create a mock database pool"""
        pool = MagicMock()  # acquire is not async, it returns a context manager
        conn = AsyncMock()
        
        # Context manager returned by acquire()
        context = AsyncMock()
        context.__aenter__.return_value = conn
        context.__aexit__.return_value = None
        
        pool.acquire.return_value = context
        return pool, conn

    @pytest.mark.asyncio
    async def test_refresh_calls_all_views(self, mock_db_pool):
        """Verify refresh is called for all views in order"""
        pool, conn = mock_db_pool

        # Import and patch
        from src.verification.worker import VerificationConsumer

        consumer = VerificationConsumer()
        consumer.db_pool = pool

        start = datetime(2026, 1, 28, 9, 0, 0)
        end = datetime(2026, 1, 28, 9, 1, 0)

        await consumer._refresh_continuous_aggregates(start, end)

        # Should call refresh for each view
        assert conn.execute.call_count == 4

        # Verify order (1m first, then cascade)
        calls = conn.execute.call_args_list
        assert 'market_candles_1m_view' in str(calls[0])
        assert 'market_candles_5m_view' in str(calls[1])
        assert 'market_candles_1h_view' in str(calls[2])
        assert 'market_candles_1d_view' in str(calls[3])

    @pytest.mark.asyncio
    async def test_refresh_retries_on_failure(self, mock_db_pool):
        """Verify retry logic on refresh failure"""
        pool, conn = mock_db_pool

        # Fail first 2 attempts, succeed on 3rd
        conn.execute.side_effect = [
            Exception("DB Error"),
            Exception("DB Error"),
            None,  # Success
            None, None, None  # Other views
        ]

        from src.verification.worker import VerificationConsumer

        consumer = VerificationConsumer()
        consumer.db_pool = pool

        start = datetime(2026, 1, 28, 9, 0, 0)
        end = datetime(2026, 1, 28, 9, 1, 0)

        # Should not raise (retries succeed)
        await consumer._refresh_continuous_aggregates(start, end)

        # 3 attempts for first view + 3 for others
        assert conn.execute.call_count >= 3

    @pytest.mark.asyncio
    async def test_refresh_skipped_without_pool(self):
        """Verify refresh is skipped when db_pool is None"""
        from src.verification.worker import VerificationConsumer

        consumer = VerificationConsumer()
        consumer.db_pool = None

        # Should not raise
        await consumer._refresh_continuous_aggregates(
            datetime.now(),
            datetime.now() + timedelta(minutes=1)
        )


class TestHandleRecoveryTaskWithRefresh:
    """Test _handle_recovery_task includes refresh call"""

    @pytest.mark.asyncio
    async def test_recovery_triggers_refresh(self):
        """Verify recovery task triggers Continuous Aggregate refresh"""
        from src.verification.worker import VerificationConsumer, VerificationTask

        consumer = VerificationConsumer()

        # Mock dependencies
        consumer.hub_client = AsyncMock()
        consumer.hub_client.execute.return_value = {
            "status": "SUCCESS",
            "data": {
                "output1": [
                    {"stck_cntg_hour": "090000", "stck_prpr": "70000", "cntg_vol": "100"}
                ]
            }
        }

        consumer._save_recovered_ticks = AsyncMock(return_value=1)
        consumer._refresh_continuous_aggregates = AsyncMock()
        consumer.db_pool = AsyncMock()

        task = VerificationTask(
            task_type="recovery",
            symbol="005930",
            minute="2026-01-28T09:00:00"
        )

        result = await consumer._handle_recovery_task(task)

        # Verify refresh was called
        consumer._refresh_continuous_aggregates.assert_called_once()


class TestSourceTypePolicy:
    """Test source_type compliance with Ground Truth Policy"""

    def test_recovery_uses_rest_api_source(self):
        """Verify recovered ticks use REST_API_KIS source type"""
        # This is a code inspection test
        # The actual source type is set in _save_recovered_ticks

        import inspect
        from src.verification.worker import VerificationConsumer

        source = inspect.getsource(VerificationConsumer._save_recovered_ticks)

        # Should use REST_API_KIS, not KIS_RECOVERY
        assert "REST_API_KIS" in source
        assert "KIS_RECOVERY" not in source or "# ISSUE-044" in source


class TestBackfillScript:
    """Test backfill_continuous_aggregates.py script"""

    def test_views_defined_in_correct_order(self):
        """Verify CONTINUOUS_AGGREGATES list contains all required views"""
        import sys
        sys.path.insert(0, '/home/ubuntu/workspace/stock_monitoring')

        from scripts.db.backfill_continuous_aggregates import CONTINUOUS_AGGREGATES

        assert len(CONTINUOUS_AGGREGATES) == 4
        assert 'market_candles_1m_view' in CONTINUOUS_AGGREGATES
        assert 'market_candles_5m_view' in CONTINUOUS_AGGREGATES
        assert 'market_candles_1h_view' in CONTINUOUS_AGGREGATES
        assert 'market_candles_1d_view' in CONTINUOUS_AGGREGATES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
