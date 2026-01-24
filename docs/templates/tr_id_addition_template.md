# TR ID 추가 템플릿

새로운 TR ID를 API Hub v2에 추가하는 방법을 단계별로 안내합니다.

---

## 📋 체크리스트

### Phase 1: 사전 조사
- [ ] 공식 API 문서에서 TR ID 확인
- [ ] Endpoint URL 확인
- [ ] Request Parameters 확인
- [ ] Response Schema 확인
- [ ] HTTP Method 확인 (GET/POST)
- [ ] 사용 목적(UseCase) 정의

### Phase 2: TR Registry 등록
- [ ] `src/api_gateway/hub/tr_registry.py` 업데이트
- [ ] TR ID 네이밍 규칙 준수 확인
- [ ] UseCase enum 추가 (필요 시)
- [ ] TRIDSpec 정의 추가

### Phase 3: Client 구현
- [ ] KISClient 또는 KiwoomClient 업데이트
- [ ] `TR_URL_MAP` (KIS) 또는 `get_url_for_tr_id()` (Kiwoom) 업데이트
- [ ] `_build_request_body()` 파라미터 빌더 추가
- [ ] `GET_TRS` set 업데이트 (GET method인 경우)
- [ ] `_handle_response()` 응답 처리 확인

### Phase 4: 테스트 작성
- [ ] Unit Test: 파라미터 빌딩 검증
- [ ] Unit Test: URL 매핑 검증
- [ ] Unit Test: TR Registry 통합 검증
- [ ] Integration Test: 실제 API 호출 검증 (선택)

### Phase 5: 문서화
- [ ] TR ID Reference 문서 업데이트
- [ ] ISSUE 문서 업데이트 (해당되는 경우)
- [ ] 변경 사항 커밋

---

## 🔧 구현 단계

### Step 1: TR Registry 업데이트

**파일**: `src/api_gateway/hub/tr_registry.py`

#### 1.1 UseCase Enum 추가 (필요한 경우)

```python
class UseCase(str, Enum):
    """TR ID 사용 목적 (Semantic Mapping)"""
    # ... 기존 UseCase들 ...
    
    # 새로운 UseCase 추가
    YOUR_NEW_USE_CASE = "YOUR_NEW_USE_CASE"  # 예: REALTIME_ORDERBOOK
```

#### 1.2 TRIDSpec 정의 추가

**KIS TR ID 추가 시**:

```python
# KIS_REGISTRY 딕셔너리에 추가
KIS_REGISTRY: Dict[str, TRIDSpec] = {
    # ... 기존 TR IDs ...
    
    "YOUR_TR_ID_HERE": TRIDSpec(
        tr_id="YOUR_TR_ID_HERE",           # 예: FHKST01020000
        provider=Provider.KIS,
        category=TRCategory.REALTIME_QUOTE,  # 적절한 카테고리 선택
        description="TR ID 설명 (한글)",
        endpoint="/uapi/your/endpoint/path",
        method="GET",                       # 또는 "POST"
        implemented=False,                  # 구현 후 True로 변경
        priority="P0",                      # P0(필수), P1(선택), P2(미래)
        documentation_url="https://apiportal.koreainvestment.com/..."
    ),
}
```

**Kiwoom API ID 추가 시**:

```python
# KIWOOM_REGISTRY 딕셔너리에 추가
KIWOOM_REGISTRY: Dict[str, TRIDSpec] = {
    # ... 기존 API IDs ...
    
    "ka10XXX": TRIDSpec(
        tr_id="ka10XXX",                   # 예: ka10082
        provider=Provider.KIWOOM,
        category=TRCategory.HISTORICAL_CANDLE,
        description="API ID 설명 (한글)",
        endpoint="/api/dostk/chart",       # Kiwoom은 대부분 동일 endpoint
        method="POST",                     # Kiwoom은 대부분 POST
        implemented=False,
        priority="P0",
        documentation_url="https://apiportal.kiwoom.com"
    ),
}
```

#### 1.3 UseCase 매핑 추가

```python
# USE_CASE_MAPPING 딕셔너리에 추가
USE_CASE_MAPPING: Dict[UseCase, Dict[Provider, str]] = {
    # ... 기존 매핑 ...
    
    UseCase.YOUR_NEW_USE_CASE: {
        Provider.KIS: "YOUR_KIS_TR_ID",
        Provider.KIWOOM: "ka10XXX",
    },
}
```

---

### Step 2: Client 구현

#### 2.1 KISClient 업데이트 (KIS TR ID인 경우)

**파일**: `src/api_gateway/hub/clients/kis_client.py`

##### 2.1.1 TR_URL_MAP 업데이트

```python
class KISClient(BaseAPIClient):
    TR_URL_MAP = {
        # ... 기존 매핑 ...
        
        "YOUR_TR_ID_HERE": "/uapi/your/endpoint/path",
    }
```

##### 2.1.2 GET_TRS 업데이트 (GET method인 경우)

```python
    GET_TRS = {
        # ... 기존 TR IDs ...
        "YOUR_TR_ID_HERE",  # GET method 사용하는 경우만
    }
```

##### 2.1.3 _build_request_body() 파라미터 빌더 추가

```python
    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """KIS API 요청 파라미터 구성"""
        
        # ... 기존 TR IDs ...
        
        # YOUR_TR_ID_HERE (설명)
        if tr_id == "YOUR_TR_ID_HERE":
            return {
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("symbol") or params.get("FID_INPUT_ISCD"),
                # 필요한 파라미터 추가
                "YOUR_PARAM_1": params.get("YOUR_PARAM_1", "default_value"),
                "YOUR_PARAM_2": params.get("YOUR_PARAM_2", ""),
            }
        
        return params
```

#### 2.2 KiwoomClient 업데이트 (Kiwoom API ID인 경우)

**파일**: `src/api_gateway/hub/clients/kiwoom_client.py`

##### 2.2.1 _build_headers() 업데이트 (필요 시)

Kiwoom은 OpenAPI+ TR ID 매핑이 필요한 경우:

```python
    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """Kiwoom API 헤더 구성 (RFC-008 준수)"""
        # OpenAPI+ TR ID → REST API ID 매핑
        api_id_map = {
            # ... 기존 매핑 ...
            "opt10XXX": "ka10XXX",  # 새 매핑 추가
        }
        api_id = api_id_map.get(tr_id, tr_id)
        # ...
```

##### 2.2.2 _build_request_body() 파라미터 빌더 추가

```python
    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Kiwoom API 요청 바디 구성 (REST API ka100xx 형식)"""
        
        # ... 기존 TR IDs ...
        
        # YOUR API ID (ka10XXX)
        if tr_id in ["ka10XXX", "opt10XXX"]:  # OpenAPI+ 매핑 포함
            return {
                "stk_cd": params["symbol"],
                "your_param_1": params.get("your_param_1", "default"),
                # 필요한 파라미터 추가
            }
        
        return params
```

##### 2.2.3 _handle_response() 응답 처리 업데이트 (필요 시)

응답 데이터 키가 다른 경우:

```python
    async def _handle_response(
        self, response: httpx.Response, tr_id: str
    ) -> Dict[str, Any]:
        """Kiwoom API 응답 처리 (RFC-008 준수)"""
        data = response.json()
        
        # 응답 데이터 키 매핑
        data_key_map = {
            "ka10080": "stk_min_pole_chart_qry",
            "ka10079": "stk_tic_chart_qry",
            "ka10XXX": "your_response_key_here",  # 새 키 추가
        }
        
        data_key = data_key_map.get(tr_id, "default_key")
        output_data = data.get(data_key, [])
        # ...
```

---

### Step 3: 테스트 작성

#### 3.1 Unit Test 작성

**KIS TR ID 테스트**: `tests/unit/api_gateway/test_kis_client.py`

```python
class TestRequestBodyBuilding:
    """요청 파라미터 빌딩 테스트"""
    
    def test_build_your_tr_id_params(self):
        """YOUR_TR_ID_HERE 파라미터 빌딩"""
        client = KISClient(app_key="test", app_secret="test")
        
        # 기본 파라미터 테스트
        params = client._build_request_body("YOUR_TR_ID_HERE", {
            "symbol": "005930",
            "YOUR_PARAM_1": "value1"
        })
        
        assert params["FID_INPUT_ISCD"] == "005930"
        assert params["YOUR_PARAM_1"] == "value1"
        assert params["FID_COND_MRKT_DIV_CODE"] == "J"  # 기본값
        
        # 전체 파라미터 테스트
        params = client._build_request_body("YOUR_TR_ID_HERE", {
            "FID_INPUT_ISCD": "035420",
            "YOUR_PARAM_1": "custom_value",
            "YOUR_PARAM_2": "param2_value"
        })
        
        assert params["FID_INPUT_ISCD"] == "035420"
        assert params["YOUR_PARAM_1"] == "custom_value"
        assert params["YOUR_PARAM_2"] == "param2_value"


class TestTRURLMapping:
    """TR ID → URL 매핑 테스트"""
    
    def test_your_tr_id_url_mapping(self):
        """YOUR_TR_ID_HERE URL 매핑 확인"""
        client = KISClient(app_key="test", app_secret="test")
        
        assert "YOUR_TR_ID_HERE" in client.TR_URL_MAP
        url = client.get_url_for_tr_id("YOUR_TR_ID_HERE")
        assert url == "/uapi/your/endpoint/path"


class TestTRRegistryIntegration:
    """TR Registry와의 통합 테스트"""
    
    def test_your_tr_id_in_registry(self):
        """TR Registry에 YOUR_TR_ID_HERE가 등록되어 있는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        spec = get_tr_spec("YOUR_TR_ID_HERE")
        assert spec is not None
        assert spec.provider.value == "KIS"
        assert spec.implemented is True
        
    def test_your_tr_id_endpoint_matches(self):
        """TR Registry endpoint와 Client URL_MAP이 일치하는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        client = KISClient(app_key="test", app_secret="test")
        spec = get_tr_spec("YOUR_TR_ID_HERE")
        
        assert spec.endpoint == client.TR_URL_MAP["YOUR_TR_ID_HERE"]
```

**Kiwoom API ID 테스트**: `tests/unit/api_gateway/test_kiwoom_client.py`

```python
class TestRequestBodyBuilding:
    """요청 파라미터 빌딩 테스트"""
    
    def test_build_ka10xxx_params(self):
        """ka10XXX 파라미터 빌딩"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        params = client._build_request_body("ka10XXX", {
            "symbol": "005930",
            "your_param_1": "value1"
        })
        
        assert params["stk_cd"] == "005930"
        assert params["your_param_1"] == "value1"
    
    def test_build_opt10xxx_legacy_mapping(self):
        """opt10XXX (OpenAPI+ TR ID) → ka10XXX 자동 매핑 테스트"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        params = client._build_request_body("opt10XXX", {
            "symbol": "005930"
        })
        
        assert params["stk_cd"] == "005930"
```

#### 3.2 TR Registry 테스트 업데이트

**파일**: `tests/unit/api_gateway/test_tr_registry.py`

구현 통계 테스트 업데이트:

```python
class TestImplementationStats:
    """구현 통계 테스트"""
    
    def test_get_implementation_stats(self):
        """구현 통계 조회"""
        stats = get_implementation_stats()
        
        # TR ID 추가로 total 숫자 증가
        assert stats["total"] == 8  # 7 → 8 (1개 추가)
        assert stats["implemented"] == 8  # 구현 완료 시
        assert stats["completion_rate"] == pytest.approx(1.0)
        
        # Provider별 통계도 업데이트
        kis_stats = stats["by_provider"]["KIS"]
        assert kis_stats["total"] == 6  # 또는 5 (provider에 따라)
        # ...
```

---

### Step 4: 문서화

#### 4.1 TR ID Reference 문서 업데이트

**KIS TR ID**: `docs/specs/api_reference/kis_tr_id_reference.md`

```markdown
### X.X YOUR_TR_ID_HERE (설명) ✅

**용도**: TR ID 사용 목적 설명

**URL**: `https://openapi.koreainvestment.com/uapi/your/endpoint/path`  
**Method**: GET (또는 POST)  
**Authority**: [KIS API Portal](https://apiportal.koreainvestment.com/...)

**Headers**:
```json
{
  "authorization": "Bearer {access_token}",
  "appkey": "{app_key}",
  "appsecret": "{app_secret}",
  "tr_id": "YOUR_TR_ID_HERE",
  "custtype": "P"
}
```

**Query Parameters** (GET인 경우):
```json
{
  "FID_COND_MRKT_DIV_CODE": "J",
  "FID_INPUT_ISCD": "005930",
  "YOUR_PARAM_1": "value1"
}
```

**Response**:
```json
{
  "output": [
    {
      "field1": "value1",
      "field2": "value2"
    }
  ],
  "rt_cd": "0",
  "msg_cd": "MCA00000",
  "msg1": "정상처리 되었습니다."
}
```

**구현 상태**: ✅ 완료 (2026-01-23)

**사용처**:
- `your-worker`: 사용 목적 설명
```

**Kiwoom API ID**: `docs/specs/api_reference/kiwoom_tr_id_reference.md`

```markdown
### X.X ka10XXX (설명) ✅

**용도**: API ID 사용 목적 설명

**URL**: `https://api.kiwoom.com/api/dostk/chart`  
**Method**: POST  
**Authority**: [Kiwoom API Portal](https://apiportal.kiwoom.com)

**Headers**:
```json
{
  "Content-Type": "application/json; charset=UTF-8",
  "authorization": "Bearer {access_token}",
  "api-id": "ka10XXX",
  "content-yn": "N",
  "User-Agent": "Mozilla/5.0"
}
```

**Body**:
```json
{
  "stk_cd": "005930",
  "your_param_1": "value1"
}
```

**Response**:
```json
{
  "your_response_key": [
    {
      "field1": "value1",
      "field2": "value2"
    }
  ],
  "return_msg": "Success",
  "return_code": "0000"
}
```

**OpenAPI+ 매핑**:
- OpenAPI+ TR ID: `opt10XXX`
- REST API에서는 `ka10XXX` 사용 필수

**구현 상태**: ✅ 완료 (2026-01-23)

**사용처**:
- `your-worker`: 사용 목적 설명
```

#### 4.2 구현 상태 표 업데이트

문서 상단의 구현 상태 표에 새 TR ID 추가:

```markdown
| Provider | TR ID | Description | 구현 상태 | 우선순위 |
|----------|-------|-------------|----------|----------|
| ... | ... | ... | ... | ... |
| KIS | YOUR_TR_ID_HERE | 설명 | ✅ 완료 (2026-01-XX) | P0 |
```

---

## 📊 구현 완료 후 체크리스트

### 코드 검증
- [ ] `poetry run pytest tests/unit/api_gateway/test_kis_client.py -v` 통과
- [ ] `poetry run pytest tests/unit/api_gateway/test_kiwoom_client.py -v` 통과
- [ ] `poetry run pytest tests/unit/api_gateway/test_tr_registry.py -v` 통과
- [ ] 모든 테스트 100% 통과 확인

### TR Registry 검증
- [ ] TR ID 형식 검증 통과 (네이밍 규칙)
- [ ] `implemented=True`로 변경
- [ ] UseCase 매핑 정상 동작 확인
- [ ] Implementation stats 업데이트 확인

### 문서 검증
- [ ] TR ID Reference 문서 업데이트 완료
- [ ] 예제 코드 정확성 확인
- [ ] 링크 정상 동작 확인

### 커밋
- [ ] 변경사항 staging: `git add -A`
- [ ] 의미 있는 커밋 메시지 작성
- [ ] 커밋 생성

---

## 🔗 참고 문서

- [TR Registry 소스코드](../src/api_gateway/hub/tr_registry.py)
- [KISClient 소스코드](../src/api_gateway/hub/clients/kis_client.py)
- [KiwoomClient 소스코드](../src/api_gateway/hub/clients/kiwoom_client.py)
- [KIS TR ID Reference](../specs/api_reference/kis_tr_id_reference.md)
- [Kiwoom TR ID Reference](../specs/api_reference/kiwoom_tr_id_reference.md)
- [Ground Truth Policy](../governance/ground_truth_policy.md)

---

## 💡 팁

### 네이밍 규칙
- **KIS TR ID**: 대문자 영숫자 10+ 글자 (예: `FHKST01010100`)
- **Kiwoom API ID**: `ka` + 5자리 숫자 (예: `ka10080`)

### UseCase 정의
- 의미 있는 이름 사용 (예: `MINUTE_CANDLE_KIS`, `TICK_DATA_KIWOOM`)
- 여러 TR ID가 같은 목적을 가질 수 있음

### 파라미터 네이밍
- KIS: FID_XXX 형식 (공식 문서 참조)
- Kiwoom: snake_case (stk_cd, tic_scope 등)

### 테스트 작성
- 최소 3가지 테스트 필요:
  1. 파라미터 빌딩 테스트
  2. URL/엔드포인트 매핑 테스트
  3. TR Registry 통합 테스트

### 문서화
- 실제 API 응답 예제 포함
- 사용 목적 명확히 기술
- 공식 문서 링크 추가

---

**Template Version**: 1.0  
**Last Updated**: 2026-01-23  
**Maintainer**: Developer Team
