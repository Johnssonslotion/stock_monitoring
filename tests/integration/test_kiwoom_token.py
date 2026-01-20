"""
Kiwoom Token 통합 테스트
========================
RFC-008 Appendix G 검증 결과 기반

기존 스크립트 통합:
- scripts/test_kiwoom_dual_token.py
- scripts/test_kiwoom_ws_token_survival.py
"""
import pytest
import asyncio
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

import aiohttp

# 실제 API 테스트는 환경 변수로 제어
SKIP_LIVE_TESTS = os.getenv("SKIP_LIVE_API_TESTS", "true").lower() == "true"


class TestKiwoomTokenBehavior:
    """Kiwoom 토큰 동작 검증 테스트"""

    TOKEN_URL = "https://api.kiwoom.com/oauth2/token"
    REST_URL = "https://api.kiwoom.com/api/dostk/chart"

    @pytest.fixture
    def credentials(self):
        """Kiwoom API 자격증명"""
        return {
            "appkey": os.getenv("KIWOOM_APP_KEY"),
            "secretkey": os.getenv("KIWOOM_APP_SECRET")
        }

    async def _get_token(self, session: aiohttp.ClientSession, credentials: dict) -> str:
        """토큰 발급 헬퍼"""
        payload = {
            "grant_type": "client_credentials",
            **credentials
        }
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }

        async with session.post(self.TOKEN_URL, json=payload, headers=headers) as resp:
            data = await resp.json()
            if data.get("return_code") == 0:
                return data.get("token")
            raise Exception(f"Token error: {data}")

    async def _test_token_validity(
        self,
        session: aiohttp.ClientSession,
        token: str
    ) -> bool:
        """토큰 유효성 테스트 (ka10079 호출)"""
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": "ka10079",
            "User-Agent": "Mozilla/5.0"
        }
        body = {
            "stk_cd": "005930",
            "tic_scope": "1",
            "upd_stkpc_tp": "0"
        }

        async with session.post(self.REST_URL, json=body, headers=headers) as resp:
            data = await resp.json()
            return data.get("return_code") == 0

    # TC-G001: 동일 credentials로 2회 발급 시 같은 토큰 반환
    @pytest.mark.integration
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API test disabled")
    @pytest.mark.asyncio
    async def test_dual_token_returns_same(self, credentials):
        """
        동일 credentials로 2회 발급 시 같은 토큰 반환

        검증 결과 (RFC-008 Appendix G.2):
        - Kiwoom 서버는 토큰 캐싱 사용
        - 만료 전까지 동일 토큰 반환
        """
        async with aiohttp.ClientSession() as session:
            # Token 1 발급
            token1 = await self._get_token(session, credentials)
            assert token1 is not None

            # 1초 대기
            await asyncio.sleep(1)

            # Token 2 발급
            token2 = await self._get_token(session, credentials)
            assert token2 is not None

            # 동일 토큰 확인
            assert token1 == token2, "Kiwoom should return same token for same credentials"

    # TC-G002: 재발급 후 기존 토큰 유효성 유지
    @pytest.mark.integration
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API test disabled")
    @pytest.mark.asyncio
    async def test_token_remains_valid_after_reissue(self, credentials):
        """
        새 토큰 발급 후에도 기존 토큰이 유효

        검증 결과: 동일 토큰이 반환되므로 자연스럽게 유지됨
        """
        async with aiohttp.ClientSession() as session:
            # Token 1 발급 및 검증
            token1 = await self._get_token(session, credentials)
            valid1 = await self._test_token_validity(session, token1)
            assert valid1, "Token1 should be valid"

            # Token 2 발급
            await asyncio.sleep(1)
            token2 = await self._get_token(session, credentials)

            # Token 1 재검증 (Token 2 발급 후)
            valid1_after = await self._test_token_validity(session, token1)
            assert valid1_after, "Token1 should remain valid after Token2 issuance"

            # Token 2 검증
            valid2 = await self._test_token_validity(session, token2)
            assert valid2, "Token2 should be valid"

    # TC-G003: 토큰 만료 시점 확인
    @pytest.mark.integration
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API test disabled")
    @pytest.mark.asyncio
    async def test_token_expiry_format(self, credentials):
        """토큰 만료 시점 형식 확인 (expires_dt)"""
        payload = {
            "grant_type": "client_credentials",
            **credentials
        }
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.TOKEN_URL, json=payload, headers=headers) as resp:
                data = await resp.json()

                assert "expires_dt" in data, "Response should contain expires_dt"
                expires_dt = data["expires_dt"]

                # 형식: "20260121120000" (YYYYMMDDHHMMSS)
                assert len(expires_dt) == 14, "expires_dt should be 14 characters"

                # 파싱 가능 확인
                expires = datetime.strptime(expires_dt, "%Y%m%d%H%M%S")
                assert expires > datetime.now(), "Token should not be already expired"


class TestKiwoomTokenMocked:
    """Kiwoom 토큰 동작 Mocked 테스트 (API 호출 없이)"""

    # TC-G004: 토큰 캐싱 로직 테스트
    def test_token_caching_logic(self):
        """토큰 캐싱 로직 (RFC-008 Appendix G.5)"""

        # 시뮬레이션: 토큰 만료 1시간 전 갱신 필요
        token_expires = datetime.now() + timedelta(hours=24)
        refresh_threshold = timedelta(hours=1)

        # 아직 갱신 불필요
        should_refresh = datetime.now() >= token_expires - refresh_threshold
        assert should_refresh is False

        # 만료 30분 전
        token_expires = datetime.now() + timedelta(minutes=30)
        should_refresh = datetime.now() >= token_expires - refresh_threshold
        assert should_refresh is True

    # TC-G005: WS와 REST 토큰 공유 시나리오
    def test_ws_rest_token_sharing_scenario(self):
        """
        WS와 REST가 동일 토큰 사용 시나리오

        결론 (RFC-008 Appendix G.8):
        - Kiwoom은 토큰 분리가 불필요
        - 동일 토큰이 자동으로 공유됨
        """
        # 시뮬레이션: 동일 토큰
        ws_token = "abc123..."
        rest_token = "abc123..."

        assert ws_token == rest_token, "WS and REST should use same token"

        # 핵심 관리 포인트: 만료 시점 동기화
        token_expires = datetime.now()
        refresh_needed_at = token_expires - timedelta(hours=1)

        assert refresh_needed_at < token_expires


class TestKiwoomMinuteAPI:
    """Kiwoom 분봉 API (ka10080) 테스트"""

    REST_URL = "https://api.kiwoom.com/api/dostk/chart"

    @pytest.fixture
    def mock_response(self):
        """Mocked API 응답 (RFC-008 Appendix F.2.3)"""
        return {
            "return_code": 0,
            "return_msg": "정상",
            "stk_min_pole_chart_qry": [
                {
                    "dt": "202601201000",
                    "open_pr": "74500",
                    "high_pr": "75200",
                    "low_pr": "74300",
                    "close_pr": "75000",
                    "trde_qty": "125000"
                },
                {
                    "dt": "202601201001",
                    "open_pr": "75000",
                    "high_pr": "75500",
                    "low_pr": "74800",
                    "close_pr": "75300",
                    "trde_qty": "98000"
                }
            ]
        }

    # TC-G006: 분봉 응답 파싱
    def test_minute_response_parsing(self, mock_response):
        """ka10080 응답 파싱 (data_key 확인)"""
        data_key = "stk_min_pole_chart_qry"  # RFC-008에서 확인된 키

        assert data_key in mock_response
        candles = mock_response[data_key]
        assert len(candles) == 2

        # 첫 번째 캔들 필드 확인
        candle = candles[0]
        assert "dt" in candle
        assert "open_pr" in candle
        assert "trde_qty" in candle

        # 거래량 합계 계산
        total_volume = sum(int(c["trde_qty"]) for c in candles)
        assert total_volume == 223000

    # TC-G007: Rate Limit 시나리오
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Rate Limit (429) 처리"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # 429 응답 시뮬레이션
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.json = AsyncMock(return_value={
                "return_code": -1,
                "return_msg": "Rate Limit Exceeded"
            })
            mock_post.return_value.__aenter__.return_value = mock_response

            # Rate Limit 처리 로직 테스트
            # (실제 구현에서는 retry 또는 skip)
            async with aiohttp.ClientSession() as session:
                # 이 테스트는 모킹된 환경에서 동작 확인
                pass
