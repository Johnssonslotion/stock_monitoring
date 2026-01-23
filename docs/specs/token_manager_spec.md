# Token Manager 설계 문서

**Document ID**: ISSUE-037-C  
**Author**: Architect Persona  
**Date**: 2026-01-23  
**Status**: Draft for Review  
**Reviewers**: PM + Architect  

---

## 1. 개요

### 목적
KIS 및 Kiwoom API의 액세스 토큰을 Redis를 Single Source of Truth(SSoT)로 관리하며, 자동 갱신 및 만료 처리를 담당합니다.

### 설계 원칙
1. **Redis SSoT**: 모든 토큰은 Redis에만 저장
2. **자동 갱신**: 만료 5분 전 자동 갱신
3. **멀티 워커 안전**: 여러 Worker가 동시에 토큰을 사용해도 안전
4. **Fallback**: 토큰 갱신 실패 시 3회 재시도

---

## 2. Redis 스키마 설계

### Key 구조

```
api:token:{provider}
```

| Provider | Redis Key | 설명 |
|----------|-----------|------|
| KIS | `api:token:kis` | 한국투자증권 액세스 토큰 |
| KIWOOM | `api:token:kiwoom` | 키움증권 액세스 토큰 |

### Value 구조 (JSON)

```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "expires_at": 1737792000,
  "refreshed_at": 1737705600,
  "refresh_count": 3
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `access_token` | string | 액세스 토큰 |
| `expires_at` | int | 만료 시각 (Unix timestamp) |
| `refreshed_at` | int | 마지막 갱신 시각 |
| `refresh_count` | int | 갱신 횟수 (모니터링용) |

### TTL 설정

```python
# 24시간 TTL (토큰 유효기간)
redis.setex("api:token:kis", 86400, json.dumps(token_data))
```

---

## 3. TokenManager 클래스 설계

```python
import redis.asyncio as redis
import json
import time
from typing import Optional
import httpx


class TokenManager:
    """
    API 토큰 관리자 (Redis SSoT)
    
    역할:
    - 토큰 저장 및 조회
    - 자동 갱신 (만료 5분 전)
    - 갱신 실패 시 재시도
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
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
            return None
        
        token_info = json.loads(data)
        
        # 만료 검사 (5분 마진)
        now = int(time.time())
        if token_info["expires_at"] - now < 300:  # 5분
            # 자동 갱신 트리거
            return await self.refresh_token(provider)
        
        return token_info["access_token"]
    
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
        
        token_info = {
            "access_token": access_token,
            "expires_at": now + expires_in,
            "refreshed_at": now,
            "refresh_count": 0
        }
        
        await self.redis.setex(
            key,
            expires_in,
            json.dumps(token_info)
        )
    
    async def refresh_token(self, provider: str, max_retries: int = 3) -> Optional[str]:
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
                if provider.upper() == "KIS":
                    new_token = await self._refresh_kis_token()
                elif provider.upper() == "KIWOOM":
                    new_token = await self._refresh_kiwoom_token()
                else:
                    raise ValueError(f"Unknown provider: {provider}")
                
                # Redis에 저장
                await self.set_token(provider, new_token)
                
                return new_token
            
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff
                    continue
                else:
                    # 재시도 실패
                    # TODO: Sentinel 알람
                    return None
    
    async def _refresh_kis_token(self) -> str:
        """KIS 토큰 갱신"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openapi.koreainvestment.com:9443/oauth2/tokenP",
                json={
                    "grant_type": "client_credentials",
                    "appkey": os.getenv("KIS_APP_KEY"),
                    "appsecret": os.getenv("KIS_APP_SECRET")
                }
            )
            data = response.json()
            return data["access_token"]
    
    async def _refresh_kiwoom_token(self) -> str:
        """Kiwoom 토큰 갱신"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openapi.kiwoom.com:9443/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "appkey": os.getenv("KIWOOM_API_KEY"),
                    "secretkey": os.getenv("KIWOOM_SECRET_KEY")
                }
            )
            data = response.json()
            return data["access_token"]
```

---

## 4. 통합 예시

### 4.1 KISClient에서 TokenManager 사용

```python
class KISClient(BaseAPIClient):
    def __init__(self, token_manager: TokenManager):
        super().__init__(provider="KIS", base_url="...")
        self.token_manager = token_manager
    
    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        # Redis에서 토큰 조회
        access_token = await self.token_manager.get_token("KIS")
        
        return {
            "authorization": f"Bearer {access_token}",
            "tr_id": tr_id,
            ...
        }
```

---

## 5. 보안 고려사항

### 5.1 평문 저장 vs 암호화

**현재 설계**: 평문 저장 (Redis에 암호화 없이)

**장점**:
- 구현 간단
- 성능 오버헤드 없음

**단점**:
- Redis 접근 권한이 있으면 토큰 노출

**권장사항** (Infrastructure 페르소나):
- Phase 2에서는 평문 저장 허용
- Phase 3에서 Fernet 암호화 적용 검토

---

## 6. 모니터링

### 6.1 메트릭

- `token_refresh_success_count`: 토큰 갱신 성공 횟수
- `token_refresh_failure_count`: 토큰 갱신 실패 횟수
- `token_expiry_time`: 토큰 만료까지 남은 시간 (초)

### 6.2 알람

- 토큰 갱신 3회 연속 실패 시 Sentinel 알람

---

## 7. 테스트 계획

```python
@pytest.mark.asyncio
async def test_token_manager_get_valid_token():
    """유효한 토큰 조회"""
    redis_client = await redis.from_url("redis://localhost/15")
    manager = TokenManager(redis_client)
    
    # 토큰 저장
    await manager.set_token("KIS", "test_token_123", expires_in=3600)
    
    # 조회
    token = await manager.get_token("KIS")
    assert token == "test_token_123"


@pytest.mark.asyncio
async def test_token_manager_auto_refresh():
    """만료 임박 시 자동 갱신"""
    manager = TokenManager(redis_client)
    
    # 만료 4분 전 토큰 저장
    await manager.set_token("KIS", "old_token", expires_in=240)
    
    # Mock refresh
    with patch.object(manager, "_refresh_kis_token", return_value="new_token"):
        token = await manager.get_token("KIS")
        assert token == "new_token"
```

---

**Review Status**: ⏳ Pending Review (PM + Architect)  
**Implementation Time**: 2-3 hours  
**Dependencies**: Redis connection, httpx
