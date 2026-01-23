"""
TokenManager - 토큰 관리자 (Redis SSoT + Redlock)

KIS, Kiwoom API의 액세스 토큰을 Redis에 저장하고 자동 갱신합니다.
Redlock 분산 락을 사용하여 여러 워커 간 토큰 갱신 경합을 방지합니다.

Reference:
    - ISSUE-040: API Hub v2 Phase 2 - Real API Integration
    - Council Review: Redlock 구현 필수 (2026-01-23)
"""
import asyncio
import json
import logging
import os
import time
import uuid
from typing import Optional, Tuple

import httpx
import redis.asyncio as redis

logger = logging.getLogger("TokenManager")

# Redlock 설정 (Ground Truth Policy 섹션 8.3 참조)
LOCK_TTL_SECONDS = 10  # 락 유효 시간 (10초)
LOCK_RETRY_DELAY = 0.5  # 락 재시도 대기 (0.5초)
LOCK_MAX_RETRIES = 5  # 락 최대 재시도 횟수


class TokenManager:
    """
    API 토큰 관리자 (Redis SSoT + Redlock 분산 락)

    역할:
    - 토큰 저장 및 조회 (Redis)
    - 자동 갱신 (만료 5분 전)
    - 갱신 실패 시 재시도 (exponential backoff)
    - Redlock 분산 락으로 멀티 워커 경합 방지

    Reference:
        - Ground Truth Policy 섹션 8.3: Token Refresh Policy
        - KIS 1분당 토큰 갱신 제한 대응
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Args:
            redis_client: Redis 비동기 클라이언트
        """
        self.redis = redis_client
        self._lock_id = str(uuid.uuid4())[:8]  # 워커 고유 ID
        logger.info(f"✅ TokenManager initialized (worker_id={self._lock_id})")

    async def get_token(self, provider: str) -> Optional[str]:
        """
        토큰 조회 (만료 검사 포함)

        Args:
            provider: "KIS" 또는 "KIWOOM"

        Returns:
            Optional[str]: 액세스 토큰 (없거나 만료 시 None)
        """
        key = f"api:token:{provider.lower()}"
        data = await self.redis.get(key)

        if not data:
            logger.warning(f"⚠️ No token found for {provider}, triggering initial refresh")
            # 토큰이 없으면 즉시 전역 락 기반 갱신 시도
            return await self.refresh_token_with_lock(provider)

        token_info = json.loads(data)

        # 만료 검사 (5분 마진)
        now = int(time.time())
        time_to_expire = token_info["expires_at"] - now

        if time_to_expire < 300:  # 5분 (Ground Truth Policy 섹션 8.3)
            logger.info(
                f"🔄 Token for {provider} expiring in {time_to_expire}s, "
                "triggering refresh with lock"
            )
            # Redlock 기반 갱신 (멀티 워커 경합 방지)
            return await self.refresh_token_with_lock(provider)

        logger.debug(
            f"✅ Token for {provider} valid (expires in {time_to_expire}s)"
        )
        return token_info["access_token"]

    # ========================================================================
    # Redlock 분산 락 메서드
    # ========================================================================

    async def _acquire_lock(self, provider: str) -> Tuple[bool, str]:
        """
        토큰 갱신을 위한 분산 락 획득

        Args:
            provider: 제공자 이름 (KIS, KIWOOM)

        Returns:
            Tuple[bool, str]: (락 획득 성공 여부, 락 키)

        Note:
            Redis SET NX EX 사용하여 원자적으로 락 획득
            락 소유자만 갱신 API 호출, 다른 워커는 대기 후 캐시 사용
        """
        lock_key = f"api:token:{provider.lower()}:lock"
        lock_value = f"{self._lock_id}:{time.time()}"

        # SET NX EX: 키가 없을 때만 설정 + TTL
        acquired = await self.redis.set(
            lock_key,
            lock_value,
            nx=True,  # Only set if not exists
            ex=LOCK_TTL_SECONDS
        )

        if acquired:
            logger.info(
                f"🔒 Lock acquired for {provider} "
                f"(worker={self._lock_id}, ttl={LOCK_TTL_SECONDS}s)"
            )
            return True, lock_key
        else:
            logger.debug(
                f"⏳ Lock not acquired for {provider} "
                f"(another worker is refreshing)"
            )
            return False, lock_key

    async def _release_lock(self, lock_key: str) -> bool:
        """
        분산 락 해제

        Args:
            lock_key: 락 키

        Returns:
            bool: 락 해제 성공 여부

        Note:
            Lua 스크립트로 원자적 해제 (자신의 락만 해제)
        """
        # Lua 스크립트: 자신이 소유한 락만 해제
        lua_script = """
        local lock_value = redis.call("GET", KEYS[1])
        if lock_value and string.find(lock_value, ARGV[1]) then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = await self.redis.eval(
                lua_script, 1, lock_key, self._lock_id
            )
            if result:
                logger.info(f"🔓 Lock released: {lock_key}")
            return bool(result)
        except Exception as e:
            logger.warning(f"⚠️ Lock release failed: {e}")
            return False

    async def _wait_for_lock_release(
        self,
        provider: str,
        max_wait: float = 5.0
    ) -> Optional[str]:
        """
        다른 워커의 락 해제 대기 후 캐시된 토큰 반환

        Args:
            provider: 제공자 이름
            max_wait: 최대 대기 시간 (초)

        Returns:
            Optional[str]: 갱신된 토큰 (없으면 None)
        """
        lock_key = f"api:token:{provider.lower()}:lock"
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 락 해제 확인
            lock_exists = await self.redis.exists(lock_key)
            if not lock_exists:
                # 락 해제됨 - 새로 갱신된 토큰 조회
                key = f"api:token:{provider.lower()}"
                data = await self.redis.get(key)
                if data:
                    token_info = json.loads(data)
                    logger.info(
                        f"✅ Got refreshed token for {provider} "
                        f"(waited {time.time() - start_time:.2f}s)"
                    )
                    return token_info["access_token"]

            await asyncio.sleep(LOCK_RETRY_DELAY)

        logger.warning(
            f"⚠️ Lock wait timeout for {provider} "
            f"(waited {max_wait}s)"
        )
        return None

    async def refresh_token_with_lock(
        self,
        provider: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Redlock 기반 토큰 갱신 (멀티 워커 안전)

        Args:
            provider: 제공자 이름 (KIS, KIWOOM)
            max_retries: 최대 재시도 횟수

        Returns:
            Optional[str]: 새로운 액세스 토큰

        Note:
            1. 락 획득 시도
            2. 성공: 토큰 갱신 API 호출
            3. 실패: 대기 후 캐시된 토큰 사용
        """
        # 1. 락 획득 시도
        acquired, lock_key = await self._acquire_lock(provider)

        if acquired:
            # 2. 락 획득 성공 - 토큰 갱신
            try:
                return await self.refresh_token(provider, max_retries)
            except Exception as e:
                logger.error(
                    f"❌ Token refresh failed for {provider}: {e}"
                )
                return None
            finally:
                # 락 해제 (성공/실패 모두)
                await self._release_lock(lock_key)
        else:
            # 3. 락 획득 실패 - 다른 워커 대기 후 캐시 사용
            token = await self._wait_for_lock_release(provider)
            if token:
                return token

            # 대기 후에도 토큰 없음 - 락 재시도
            for attempt in range(LOCK_MAX_RETRIES):
                acquired, lock_key = await self._acquire_lock(provider)
                if acquired:
                    try:
                        return await self.refresh_token(provider, max_retries)
                    finally:
                        await self._release_lock(lock_key)

                await asyncio.sleep(LOCK_RETRY_DELAY * (attempt + 1))

            logger.error(
                f"❌ Failed to refresh token for {provider} "
                f"after {LOCK_MAX_RETRIES} lock attempts"
            )
            return None

    async def set_token(
        self,
        provider: str,
        access_token: str,
        expires_in: int = 86400
    ):
        """
        토큰 저장

        Args:
            provider: "KIS" 또는 "KIWOOM"
            access_token: 액세스 토큰
            expires_in: 유효 기간 (초, 기본 24시간)
        """
        key = f"api:token:{provider.lower()}"
        now = int(time.time())

        # 기존 토큰 정보 조회 (refresh_count 유지)
        old_data = await self.redis.get(key)
        refresh_count = 0
        if old_data:
            old_info = json.loads(old_data)
            refresh_count = old_info.get("refresh_count", 0) + 1

        token_info = {
            "access_token": access_token,
            "expires_at": now + expires_in,
            "refreshed_at": now,
            "refresh_count": refresh_count
        }

        await self.redis.setex(
            key,
            expires_in,
            json.dumps(token_info)
        )

        logger.info(
            f"✅ Token saved for {provider} (expires in {expires_in}s, "
            f"refresh_count={refresh_count})"
        )

    async def refresh_token(
        self,
        provider: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        토큰 갱신 (재시도 포함)

        Args:
            provider: "KIS" 또는 "KIWOOM"
            max_retries: 최대 재시도 횟수

        Returns:
            Optional[str]: 새로운 액세스 토큰
        """
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"🔄 Refreshing {provider} token "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                if provider.upper() == "KIS":
                    new_token = await self._refresh_kis_token()
                elif provider.upper() == "KIWOOM":
                    new_token = await self._refresh_kiwoom_token()
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                # Redis에 저장
                await self.set_token(provider, new_token)

                logger.info(f"✅ {provider} token refreshed successfully")
                return new_token

            except Exception as e:
                logger.error(
                    f"❌ Failed to refresh {provider} token "
                    f"(attempt {attempt + 1}): {e}"
                )

                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    logger.info(f"⏳ Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    continue
                else:
                    logger.error(
                        f"❌ Token refresh failed after {max_retries} "
                        f"attempts for {provider}"
                    )
                    # TODO: Sentinel 알람 발행
                    return None

    async def _refresh_kis_token(self) -> str:
        """KIS 토큰 갱신"""
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        base_url = os.getenv(
            "KIS_BASE_URL",
            "https://openapi.koreainvestment.com:9443"
        )

        if not app_key or not app_secret:
            raise ValueError("KIS_APP_KEY and KIS_APP_SECRET are required")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/oauth2/tokenP",
                json={
                    "grant_type": "client_credentials",
                    "appkey": app_key,
                    "appsecret": app_secret
                },
                timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"❌ KIS token refresh error ({response.status_code}): {response.text}")
                response.raise_for_status()

            data = response.json()
            if data.get("rt_cd") != "0":
                raise Exception(f"KIS token refresh error: {data.get('msg1')}")

            return data["access_token"]

    async def _refresh_kiwoom_token(self) -> str:
        """Kiwoom 토큰 갱신"""
        api_key = os.getenv("KIWOOM_API_KEY") or os.getenv("KIWOOM_APP_KEY")
        secret_key = os.getenv("KIWOOM_SECRET_KEY") or os.getenv("KIWOOM_APP_SECRET")
        base_url = os.getenv(
            "KIWOOM_API_URL",
            "https://openapi.kiwoom.com:9443"
        )

        if not api_key or not secret_key:
            raise ValueError(
                "KIWOOM_API_KEY and KIWOOM_SECRET_KEY are required"
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "appkey": api_key,
                    "secretkey": secret_key
                },
                timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"❌ Kiwoom token refresh error ({response.status_code}): {response.text}")
                response.raise_for_status()

            data = response.json()
            if data.get("rsp_cd") != "0000":
                raise Exception(
                    f"Kiwoom token refresh error: {data.get('rsp_msg')}"
                )

            return data["access_token"]
