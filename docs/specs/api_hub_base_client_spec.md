# BaseAPIClient 설계 문서

**Document ID**: ISSUE-037-A  
**Author**: Developer Persona  
**Date**: 2026-01-23  
**Status**: Draft for Review  
**Reviewers**: Architect + Developer  

---

## 1. 개요 (Overview)

### 목적
KIS와 Kiwoom API 클라이언트의 공통 로직을 추상화하여 코드 중복을 제거하고, 일관된 에러 처리 및 타임아웃 관리를 제공합니다.

### 설계 원칙
1. **DRY (Don't Repeat Yourself)**: 인증, 헤더 구성, 응답 파싱 등 공통 로직 단일화
2. **Open/Closed Principle**: 새로운 Provider 추가 시 기존 코드 수정 없이 확장 가능
3. **Fail-Fast**: 타임아웃, 네트워크 오류 등 즉시 감지 및 보고
4. **Async-First**: 모든 API 호출은 비동기 패턴 사용

---

## 2. 클래스 계층 구조 (Class Hierarchy)

```
BaseAPIClient (Abstract)
├── KISClient (Concrete)
└── KiwoomClient (Concrete)
```

### 상속 관계
- `BaseAPIClient`: 추상 베이스 클래스 (ABC)
- `KISClient`: 한국투자증권 API 구현
- `KiwoomClient`: 키움증권 API 구현

---

## 3. BaseAPIClient 인터페이스 설계

### 3.1 추상 메서드 (Abstract Methods)

구현 클래스가 반드시 오버라이드해야 하는 메서드:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
import asyncio


class BaseAPIClient(ABC):
    """
    REST API 클라이언트 추상 베이스 클래스
    
    KIS, Kiwoom 등 모든 API 클라이언트의 공통 인터페이스를 정의합니다.
    """
    
    def __init__(self, provider: str, base_url: str, timeout: float = 10.0):
        """
        Args:
            provider: 제공자 이름 (예: "KIS", "KIWOOM")
            base_url: API Base URL
            timeout: 요청 타임아웃 (초 단위, 기본값 10초)
        """
        self.provider = provider
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @abstractmethod
    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """
        API 요청 헤더 구성 (Provider별 구현 필요)
        
        Args:
            tr_id: 거래 ID (예: FHKST01010100)
            **kwargs: 추가 헤더 파라미터
        
        Returns:
            Dict[str, str]: HTTP 헤더 딕셔너리
        
        Example:
            # KIS 구현
            return {
                "Content-Type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id
            }
        """
        pass
    
    @abstractmethod
    def _build_request_body(self, tr_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 요청 바디 구성 (Provider별 구현 필요)
        
        Args:
            tr_id: 거래 ID
            params: 요청 파라미터
        
        Returns:
            Dict[str, Any]: 요청 바디 (JSON)
        
        Example:
            # KIS 분봉 조회
            return {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": params["symbol"],
                "FID_INPUT_HOUR_1": params.get("timeframe", "1"),
                "FID_PW_DATA_INCU_YN": "Y"
            }
        """
        pass
    
    @abstractmethod
    async def _handle_response(self, response: httpx.Response, tr_id: str) -> Dict[str, Any]:
        """
        API 응답 파싱 및 검증 (Provider별 구현 필요)
        
        Args:
            response: httpx Response 객체
            tr_id: 거래 ID
        
        Returns:
            Dict[str, Any]: 정규화된 응답 데이터
        
        Raises:
            APIError: API 에러 발생 시
            ValidationError: 응답 데이터 검증 실패 시
        
        Example:
            # KIS 응답 처리
            data = response.json()
            if data["rt_cd"] != "0":
                raise APIError(f"KIS API Error: {data['msg1']}")
            return {
                "status": "success",
                "data": data["output2"],  # 분봉 데이터
                "message": data.get("msg1", "")
            }
        """
        pass
    
    @abstractmethod
    async def refresh_token(self) -> str:
        """
        액세스 토큰 갱신 (Provider별 구현 필요)
        
        Returns:
            str: 새로운 액세스 토큰
        
        Raises:
            AuthenticationError: 토큰 갱신 실패 시
        
        Note:
            - 토큰 만료 5분 전 자동 호출
            - Redis에 저장된 토큰을 갱신
        """
        pass
```

---

### 3.2 공통 메서드 (Concrete Methods)

모든 구현 클래스가 공유하는 메서드:

```python
    async def connect(self):
        """HTTP 클라이언트 초기화"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": f"APIHub/{self.provider}"}
            )
    
    async def disconnect(self):
        """HTTP 클라이언트 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def execute(
        self,
        tr_id: str,
        params: Dict[str, Any],
        method: str = "POST"
    ) -> Dict[str, Any]:
        """
        API 요청 실행 (공통 로직)
        
        Args:
            tr_id: 거래 ID
            params: 요청 파라미터
            method: HTTP 메서드 (기본값: POST)
        
        Returns:
            Dict[str, Any]: 정규화된 응답 데이터
        
        Raises:
            TimeoutError: 타임아웃 발생 시
            APIError: API 에러 발생 시
            NetworkError: 네트워크 오류 발생 시
        """
        if self._client is None:
            await self.connect()
        
        try:
            # 타임아웃 적용
            result = await asyncio.wait_for(
                self._execute_with_retry(tr_id, params, method),
                timeout=self.timeout
            )
            return result
        
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"{self.provider} API timeout after {self.timeout}s "
                f"(tr_id={tr_id})"
            )
        except Exception as e:
            await self._handle_error(tr_id, e)
            raise
    
    async def _execute_with_retry(
        self,
        tr_id: str,
        params: Dict[str, Any],
        method: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        재시도 로직이 포함된 API 실행
        
        Args:
            tr_id: 거래 ID
            params: 요청 파라미터
            method: HTTP 메서드
            max_retries: 최대 재시도 횟수
        
        Returns:
            Dict[str, Any]: 정규화된 응답 데이터
        
        Note:
            - 5xx 에러: 재시도 (exponential backoff)
            - 4xx 에러: 즉시 실패 (재시도 안 함)
            - 429 에러: Rate Limit 초과, Circuit Breaker 트리거
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 헤더 및 바디 구성
                headers = self._build_headers(tr_id)
                body = self._build_request_body(tr_id, params)
                
                # HTTP 요청
                if method.upper() == "GET":
                    response = await self._client.get(
                        url=f"/{tr_id}",
                        headers=headers,
                        params=body
                    )
                else:  # POST
                    response = await self._client.post(
                        url=f"/{tr_id}",
                        headers=headers,
                        json=body
                    )
                
                # 응답 처리
                response.raise_for_status()
                return await self._handle_response(response, tr_id)
            
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                
                # 429 Rate Limit: 재시도 안 함, Circuit Breaker로 전달
                if status_code == 429:
                    raise RateLimitError(
                        f"{self.provider} Rate Limit exceeded (tr_id={tr_id})"
                    )
                
                # 4xx 클라이언트 에러: 재시도 안 함
                if 400 <= status_code < 500:
                    raise APIError(
                        f"{self.provider} Client Error {status_code}: "
                        f"{e.response.text} (tr_id={tr_id})"
                    )
                
                # 5xx 서버 에러: 재시도
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt  # exponential backoff
                    await asyncio.sleep(backoff)
                    last_error = e
                    continue
                else:
                    raise APIError(
                        f"{self.provider} Server Error {status_code} after "
                        f"{max_retries} retries (tr_id={tr_id})"
                    )
            
            except httpx.NetworkError as e:
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    await asyncio.sleep(backoff)
                    last_error = e
                    continue
                else:
                    raise NetworkError(
                        f"{self.provider} Network error after {max_retries} "
                        f"retries: {str(e)} (tr_id={tr_id})"
                    )
        
        # 모든 재시도 실패
        raise last_error
    
    async def _handle_error(self, tr_id: str, exception: Exception):
        """
        에러 로깅 및 추가 처리 (공통 로직)
        
        Args:
            tr_id: 거래 ID
            exception: 발생한 예외
        
        Note:
            - Sentinel 알람 발행
            - Redis에 에러 기록
            - Circuit Breaker 상태 업데이트
        """
        import logging
        logger = logging.getLogger(f"{self.provider}Client")
        
        logger.error(
            f"❌ API Error: {self.provider} {tr_id} - {type(exception).__name__}: {str(exception)}",
            exc_info=True
        )
        
        # TODO: Sentinel 알람 발행
        # await publish_alert(f"api:{self.provider}:error", {
        #     "tr_id": tr_id,
        #     "error": str(exception),
        #     "timestamp": datetime.utcnow().isoformat()
        # })
```

---

## 4. KISClient 구현 예시

```python
from typing import Dict, Any
import os


class KISClient(BaseAPIClient):
    """
    한국투자증권 REST API 클라이언트
    
    Reference:
        https://apiportal.koreainvestment.com/apiservice/
    """
    
    def __init__(
        self,
        app_key: str = None,
        app_secret: str = None,
        access_token: str = None,
        base_url: str = "https://openapi.koreainvestment.com:9443"
    ):
        super().__init__(
            provider="KIS",
            base_url=base_url,
            timeout=10.0
        )
        
        self.app_key = app_key or os.getenv("KIS_APP_KEY")
        self.app_secret = app_secret or os.getenv("KIS_APP_SECRET")
        self.access_token = access_token  # Redis에서 로드
        
        if not self.app_key or not self.app_secret:
            raise ValueError("KIS_APP_KEY and KIS_APP_SECRET are required")
    
    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """KIS API 헤더 구성"""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"  # 개인
        }
    
    def _build_request_body(self, tr_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """KIS API 요청 바디 구성"""
        
        # 분봉 조회 (FHKST01010100)
        if tr_id == "FHKST01010100":
            return {
                "FID_COND_MRKT_DIV_CODE": "J",  # 주식
                "FID_INPUT_ISCD": params["symbol"],
                "FID_INPUT_HOUR_1": params.get("timeframe", "1"),  # 1분봉
                "FID_PW_DATA_INCU_YN": "Y"
            }
        
        # 다른 TR ID 처리...
        return params
    
    async def _handle_response(self, response: httpx.Response, tr_id: str) -> Dict[str, Any]:
        """KIS API 응답 처리"""
        data = response.json()
        
        # 에러 체크
        rt_cd = data.get("rt_cd")
        if rt_cd != "0":
            error_msg = data.get("msg1", "Unknown error")
            raise APIError(f"KIS API Error ({rt_cd}): {error_msg}")
        
        # 정규화된 데이터 반환
        return {
            "status": "success",
            "provider": "KIS",
            "tr_id": tr_id,
            "data": data.get("output2", []),  # 분봉 데이터
            "message": data.get("msg1", "")
        }
    
    async def refresh_token(self) -> str:
        """KIS 토큰 갱신"""
        response = await self._client.post(
            url="/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
        )
        
        data = response.json()
        self.access_token = data["access_token"]
        
        # Redis에 저장
        # await redis.setex(f"api:token:kis", 86400, self.access_token)
        
        return self.access_token
```

---

## 5. KiwoomClient 구현 예시

```python
class KiwoomClient(BaseAPIClient):
    """
    키움증권 REST API 클라이언트
    
    Reference:
        https://apiportal.kiwoom.com/
    """
    
    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        access_token: str = None,
        base_url: str = "https://openapi.kiwoom.com:9443"
    ):
        super().__init__(
            provider="KIWOOM",
            base_url=base_url,
            timeout=10.0
        )
        
        self.api_key = api_key or os.getenv("KIWOOM_API_KEY")
        self.secret_key = secret_key or os.getenv("KIWOOM_SECRET_KEY")
        self.access_token = access_token
        
        if not self.api_key or not self.secret_key:
            raise ValueError("KIWOOM_API_KEY and KIWOOM_SECRET_KEY are required")
    
    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """Kiwoom API 헤더 구성"""
        return {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "apikey": self.api_key,
            "tr_cd": tr_id
        }
    
    def _build_request_body(self, tr_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Kiwoom API 요청 바디 구성"""
        
        # 분봉 조회 (opt10081)
        if tr_id == "opt10081":
            return {
                "종목코드": params["symbol"],
                "틱범위": params.get("timeframe", "1"),
                "수정주가구분": "1"
            }
        
        return params
    
    async def _handle_response(self, response: httpx.Response, tr_id: str) -> Dict[str, Any]:
        """Kiwoom API 응답 처리"""
        data = response.json()
        
        # 에러 체크
        if data.get("rsp_cd") != "0000":
            error_msg = data.get("rsp_msg", "Unknown error")
            raise APIError(f"Kiwoom API Error: {error_msg}")
        
        return {
            "status": "success",
            "provider": "KIWOOM",
            "tr_id": tr_id,
            "data": data.get("output", []),
            "message": data.get("rsp_msg", "")
        }
    
    async def refresh_token(self) -> str:
        """Kiwoom 토큰 갱신"""
        response = await self._client.post(
            url="/oauth/token",
            json={
                "grant_type": "client_credentials",
                "appkey": self.api_key,
                "secretkey": self.secret_key
            }
        )
        
        data = response.json()
        self.access_token = data["access_token"]
        
        return self.access_token
```

---

## 6. 예외 클래스 정의

```python
class APIError(Exception):
    """API 호출 실패"""
    pass


class RateLimitError(APIError):
    """Rate Limit 초과"""
    pass


class AuthenticationError(APIError):
    """인증 실패"""
    pass


class NetworkError(APIError):
    """네트워크 오류"""
    pass


class ValidationError(APIError):
    """응답 데이터 검증 실패"""
    pass
```

---

## 7. 타임아웃 처리 전략

### 7.1 기본 타임아웃: 10초
- 모든 API 요청은 10초 내에 완료되어야 함
- `asyncio.wait_for(timeout=10)` 사용

### 7.2 계층별 타임아웃
```python
# 전체 요청 타임아웃 (10초)
result = await asyncio.wait_for(
    client.execute(tr_id, params),
    timeout=10.0
)

# 내부 HTTP 타임아웃 (8초)
# httpx.AsyncClient(timeout=8.0)
```

### 7.3 타임아웃 발생 시 처리
1. `TimeoutError` 예외 발생
2. Circuit Breaker 실패 카운트 증가
3. Sentinel 알람 발행
4. 재시도 안 함 (Worker가 다음 태스크로 진행)

---

## 8. 통합 예시

### 8.1 Worker에서 사용

```python
# src/api_gateway/hub/worker.py

from .clients.base import BaseAPIClient
from .clients.kis_client import KISClient
from .clients.kiwoom_client import KiwoomClient


class RestApiWorker:
    def __init__(self, enable_mock: bool = False):
        self.enable_mock = enable_mock
        
        if enable_mock:
            self.clients = {
                "KIS": MockClient("KIS"),
                "KIWOOM": MockClient("KIWOOM")
            }
        else:
            self.clients = {
                "KIS": KISClient(),
                "KIWOOM": KiwoomClient()
            }
    
    async def setup(self):
        """클라이언트 초기화"""
        for client in self.clients.values():
            if isinstance(client, BaseAPIClient):
                await client.connect()
    
    async def cleanup(self):
        """클라이언트 종료"""
        for client in self.clients.values():
            if isinstance(client, BaseAPIClient):
                await client.disconnect()
```

---

## 9. 테스트 전략

### 9.1 단위 테스트 (Mock 기반)
```python
# tests/unit/test_base_client.py

@pytest.mark.asyncio
async def test_kis_client_execute_success():
    """KISClient 정상 실행 테스트"""
    client = KISClient(
        app_key="test_key",
        app_secret="test_secret",
        access_token="test_token"
    )
    
    # httpx.AsyncClient를 Mock으로 대체
    with patch.object(client, "_client") as mock_client:
        mock_response = httpx.Response(
            status_code=200,
            json={"rt_cd": "0", "output2": [{"price": 1000}]}
        )
        mock_client.post = AsyncMock(return_value=mock_response)
        
        result = await client.execute("FHKST01010100", {"symbol": "005930"})
        
        assert result["status"] == "success"
        assert result["provider"] == "KIS"
```

### 9.2 타임아웃 테스트
```python
@pytest.mark.asyncio
async def test_timeout_handling():
    """타임아웃 처리 테스트"""
    client = KISClient(app_key="test", app_secret="test", access_token="test")
    client.timeout = 0.1  # 100ms
    
    with patch.object(client, "_execute_with_retry", side_effect=asyncio.sleep(1)):
        with pytest.raises(TimeoutError):
            await client.execute("FHKST01010100", {"symbol": "005930"})
```

---

## 10. 파일 구조

```
src/api_gateway/hub/
├── clients/
│   ├── __init__.py
│   ├── base.py              # BaseAPIClient (추상 클래스)
│   ├── kis_client.py        # KISClient 구현
│   ├── kiwoom_client.py     # KiwoomClient 구현
│   └── exceptions.py        # APIError, RateLimitError 등
├── worker.py                # RestApiWorker (기존)
├── dispatcher.py            # TaskDispatcher (기존)
└── ...

tests/unit/
├── test_base_client.py      # BaseAPIClient 테스트
├── test_kis_client.py       # KISClient 테스트 (Fixture 기반)
└── test_kiwoom_client.py    # KiwoomClient 테스트 (Fixture 기반)
```

---

## 11. 체크리스트 (Checklist)

### 구현 전 확인 사항
- [ ] `httpx` 패키지 설치 확인 (`pip install httpx`)
- [ ] 환경변수 설정 (KIS_APP_KEY, KIS_APP_SECRET 등)
- [ ] Redis Token Manager 연동 준비

### 구현 시 주의사항
- [ ] 모든 API 호출에 타임아웃 적용 (`asyncio.wait_for`)
- [ ] 5xx 에러는 재시도, 4xx 에러는 즉시 실패
- [ ] 429 Rate Limit 에러는 Circuit Breaker로 전달
- [ ] 민감정보(API Key, Token) 로그 출력 금지

### 테스트 확인 사항
- [ ] Mock 기반 단위 테스트 작성
- [ ] 타임아웃 처리 테스트
- [ ] 재시도 로직 테스트
- [ ] 에러 핸들링 테스트

---

## 12. 다음 단계 (Next Steps)

1. **Architect 리뷰**: 아키텍처 검증
2. **Developer 리뷰**: 코드 품질 및 구현 가능성 검증
3. **API Fixture 수집** (ISSUE-037-B): 실제 API 응답 샘플 수집
4. **BaseAPIClient 구현**: 리뷰 승인 후 실제 코드 작성

---

**Review Status**: ⏳ Pending Review (Architect + Developer)  
**Estimated Implementation Time**: 4-6 hours  
**Dependencies**: ISSUE-037-B (API Fixture 수집)
