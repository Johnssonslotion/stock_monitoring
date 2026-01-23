"""
TokenManager 단위 테스트

Redis Mocking을 통해 토큰 관리 로직을 검증합니다.
"""
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api_gateway.hub.token_manager import TokenManager


# ============================================================================
# TokenManager Tests
# ============================================================================

class TestTokenManager:
    """TokenManager 단위 테스트"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis 클라이언트"""
        redis = AsyncMock()
        return redis
    
    @pytest.fixture
    def token_manager(self, mock_redis):
        """TokenManager 인스턴스"""
        return TokenManager(mock_redis)
    
    @pytest.mark.asyncio
    async def test_get_token_returns_valid_token(self, token_manager, mock_redis):
        """유효한 토큰 조회 테스트"""
        now = int(time.time())
        token_data = {
            "access_token": "valid_token_123",
            "expires_at": now + 3600,  # 1시간 후 만료
            "refreshed_at": now,
            "refresh_count": 0
        }
        mock_redis.get.return_value = json.dumps(token_data)
        
        result = await token_manager.get_token("KIS")
        
        assert result == "valid_token_123"
        mock_redis.get.assert_called_once_with("api:token:kis")
    
    @pytest.mark.asyncio
    async def test_get_token_returns_none_when_missing(self, token_manager, mock_redis):
        """토큰 없을 때 None 반환"""
        mock_redis.get.return_value = None
        
        result = await token_manager.get_token("KIS")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_token_triggers_refresh_when_expiring(self, token_manager, mock_redis):
        """만료 임박 시 자동 갱신 트리거 (Redlock 기반)"""
        now = int(time.time())
        token_data = {
            "access_token": "expiring_token",
            "expires_at": now + 200,  # 5분 미만 (자동 갱신 조건)
            "refreshed_at": now - 3000,
            "refresh_count": 1
        }
        mock_redis.get.return_value = json.dumps(token_data)

        # refresh_token_with_lock을 mock (Redlock 기반 갱신)
        with patch.object(
            token_manager, "refresh_token_with_lock", return_value="new_token"
        ) as mock_refresh:
            result = await token_manager.get_token("KIS")

            mock_refresh.assert_called_once_with("KIS")
            assert result == "new_token"
    
    @pytest.mark.asyncio
    async def test_set_token_stores_in_redis(self, token_manager, mock_redis):
        """토큰 저장 테스트"""
        mock_redis.get.return_value = None  # 이전 토큰 없음
        
        await token_manager.set_token("KIS", "new_access_token", expires_in=3600)
        
        # setex 호출 확인
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "api:token:kis"
        assert call_args[0][1] == 3600
        
        # 저장된 데이터 검증
        stored_data = json.loads(call_args[0][2])
        assert stored_data["access_token"] == "new_access_token"
        assert stored_data["refresh_count"] == 0
    
    @pytest.mark.asyncio
    async def test_set_token_increments_refresh_count(self, token_manager, mock_redis):
        """갱신 시 refresh_count 증가 확인"""
        old_token = {
            "access_token": "old_token",
            "expires_at": int(time.time()) + 100,
            "refreshed_at": int(time.time()) - 1000,
            "refresh_count": 5
        }
        mock_redis.get.return_value = json.dumps(old_token)
        
        await token_manager.set_token("KIS", "new_token", expires_in=3600)
        
        stored_data = json.loads(mock_redis.setex.call_args[0][2])
        assert stored_data["refresh_count"] == 6
    
    @pytest.mark.asyncio
    async def test_refresh_token_with_retries(self, token_manager, mock_redis):
        """재시도 로직 테스트"""
        call_count = 0

        async def failing_refresh():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API Error")
            return "refreshed_token"

        with patch.object(token_manager, "_refresh_kis_token", side_effect=failing_refresh):
            # set_token도 mock 처리
            mock_redis.get.return_value = None

            result = await token_manager.refresh_token("KIS", max_retries=3)

        assert call_count == 3  # 3번째에 성공
        assert result == "refreshed_token"


# ============================================================================
# Redlock 분산 락 테스트
# ============================================================================

class TestTokenManagerRedlock:
    """TokenManager Redlock 분산 락 테스트"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis 클라이언트"""
        redis = AsyncMock()
        return redis

    @pytest.fixture
    def token_manager(self, mock_redis):
        """TokenManager 인스턴스"""
        return TokenManager(mock_redis)

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self, token_manager, mock_redis):
        """락 획득 성공 테스트"""
        mock_redis.set.return_value = True  # SET NX 성공

        acquired, lock_key = await token_manager._acquire_lock("KIS")

        assert acquired is True
        assert lock_key == "api:token:kis:lock"
        mock_redis.set.assert_called_once()
        # NX=True, EX=10 확인
        call_kwargs = mock_redis.set.call_args[1]
        assert call_kwargs["nx"] is True
        assert call_kwargs["ex"] == 10

    @pytest.mark.asyncio
    async def test_acquire_lock_failure(self, token_manager, mock_redis):
        """락 획득 실패 테스트 (다른 워커가 보유 중)"""
        mock_redis.set.return_value = False  # SET NX 실패

        acquired, lock_key = await token_manager._acquire_lock("KIS")

        assert acquired is False
        assert lock_key == "api:token:kis:lock"

    @pytest.mark.asyncio
    async def test_release_lock_success(self, token_manager, mock_redis):
        """락 해제 성공 테스트"""
        mock_redis.eval.return_value = 1  # DEL 성공

        result = await token_manager._release_lock("api:token:kis:lock")

        assert result is True
        mock_redis.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_lock_not_owned(self, token_manager, mock_redis):
        """다른 워커의 락 해제 시도 (실패)"""
        mock_redis.eval.return_value = 0  # 자신의 락이 아님

        result = await token_manager._release_lock("api:token:kis:lock")

        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_token_with_lock_acquires_and_releases(
        self, token_manager, mock_redis
    ):
        """Redlock 획득 → 갱신 → 해제 전체 플로우 테스트"""
        mock_redis.set.return_value = True  # 락 획득 성공
        mock_redis.eval.return_value = 1  # 락 해제 성공
        mock_redis.get.return_value = None  # 이전 토큰 없음

        with patch.object(
            token_manager, "refresh_token", return_value="new_token"
        ) as mock_refresh:
            result = await token_manager.refresh_token_with_lock("KIS")

        assert result == "new_token"
        mock_refresh.assert_called_once_with("KIS", 3)
        # 락 획득 및 해제 확인
        mock_redis.set.assert_called_once()
        mock_redis.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_with_lock_waits_for_other_worker(
        self, token_manager, mock_redis
    ):
        """다른 워커가 갱신 중일 때 대기 후 캐시 사용"""
        # 첫 번째 락 획득 실패
        mock_redis.set.return_value = False

        # 락 대기 중 해제됨
        mock_redis.exists.side_effect = [True, True, False]  # 3번째에 락 해제

        # 갱신된 토큰 있음
        now = int(time.time())
        new_token_data = {
            "access_token": "refreshed_by_other_worker",
            "expires_at": now + 3600,
            "refreshed_at": now,
            "refresh_count": 1
        }

        # get 호출 시 순서: 첫 조회 (락 대기 중) → 락 해제 후 조회
        mock_redis.get.return_value = json.dumps(new_token_data)

        result = await token_manager.refresh_token_with_lock("KIS")

        assert result == "refreshed_by_other_worker"

    @pytest.mark.asyncio
    async def test_refresh_token_with_lock_releases_on_error(
        self, token_manager, mock_redis
    ):
        """갱신 실패 시에도 락 해제 확인"""
        mock_redis.set.return_value = True  # 락 획득 성공
        mock_redis.eval.return_value = 1  # 락 해제 성공

        with patch.object(
            token_manager, "refresh_token", side_effect=Exception("API Error")
        ):
            result = await token_manager.refresh_token_with_lock("KIS")

        # 에러 발생해도 락은 해제됨
        assert result is None
        mock_redis.eval.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_refresh_only_one_succeeds(self, mock_redis):
        """동시 갱신 시도 시 한 워커만 성공 (시뮬레이션)"""
        # 두 개의 TokenManager 인스턴스 (서로 다른 워커 시뮬레이션)
        tm1 = TokenManager(mock_redis)
        tm2 = TokenManager(mock_redis)

        # tm1이 먼저 락 획득
        lock_holder = None

        async def mock_set(key, value, nx=False, ex=None):
            nonlocal lock_holder
            if nx and lock_holder is None:
                lock_holder = value
                return True
            return False

        mock_redis.set = AsyncMock(side_effect=mock_set)
        mock_redis.eval.return_value = 1
        mock_redis.get.return_value = None
        mock_redis.exists.return_value = False

        with patch.object(tm1, "refresh_token", return_value="token_from_tm1"):
            with patch.object(tm2, "refresh_token", return_value="token_from_tm2"):
                # tm1이 먼저 락 획득
                result1 = await tm1.refresh_token_with_lock("KIS")

        # tm1만 실제 갱신 수행
        assert result1 == "token_from_tm1"
