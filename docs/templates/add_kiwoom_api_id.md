# Kiwoom API ID 추가 가이드

키움증권(Kiwoom) REST API의 새로운 API ID를 API Hub v2에 추가하는 방법을 단계별로 안내합니다.

---

## 📋 체크리스트

### Phase 1: 사전 조사
- [ ] [Kiwoom API Portal](https://apiportal.kiwoom.com/)에서 API ID 확인
- [ ] REST API ID 확인 (ka + 5자리 숫자)
- [ ] OpenAPI+ TR ID 확인 (opt + 5자리 숫자)
- [ ] Endpoint URL 확인 (대부분 `/api/dostk/chart`)
- [ ] Request Body 파라미터 확인
- [ ] Response Schema 확인
- [ ] 사용 목적(UseCase) 정의

### Phase 2: TR Registry 등록
- [ ] `src/api_gateway/hub/tr_registry.py` 업데이트
- [ ] API ID 네이밍 규칙 준수 (ka + 5자리 숫자)
- [ ] UseCase enum 추가 (필요 시)
- [ ] TRIDSpec 정의 추가

### Phase 3: KiwoomClient 구현
- [ ] `src/api_gateway/hub/clients/kiwoom_client.py` 업데이트
- [ ] `_build_headers()` OpenAPI+ 매핑 추가 (필요 시)
- [ ] `_build_request_body()` 파라미터 빌더 추가
- [ ] `_handle_response()` 응답 키 매핑 추가 (필요 시)

### Phase 4: 테스트 작성
- [ ] `tests/unit/api_gateway/test_kiwoom_client.py` 업데이트
- [ ] Unit Test: 파라미터 빌딩 검증
- [ ] Unit Test: OpenAPI+ 매핑 검증
- [ ] Unit Test: TR Registry 통합 검증

### Phase 5: 문서화
- [ ] `docs/specs/api_reference/kiwoom_tr_id_reference.md` 업데이트
- [ ] 변경 사항 커밋

---

## 🔧 구현 단계

### Step 1: TR Registry 등록

**파일**: `src/api_gateway/hub/tr_registry.py`

#### 1.1 UseCase Enum 추가 (필요한 경우)

```python
class UseCase(str, Enum):
    """TR ID 사용 목적 (Semantic Mapping)"""
    # ... 기존 UseCase들 ...
    
    # 새로운 UseCase 추가
    YOUR_USE_CASE_KIWOOM = "YOUR_USE_CASE_KIWOOM"  # 예: DAILY_CANDLE_KIWOOM
```

#### 1.2 KIWOOM_REGISTRY에 TRIDSpec 추가

```python
# KIWOOM_REGISTRY 딕셔너리에 추가
KIWOOM_REGISTRY: Dict[str, TRIDSpec] = {
    # ... 기존 API IDs ...
    
    "ka10XXX": TRIDSpec(
        tr_id="ka10XXX",                    # 예: ka10082
        provider=Provider.KIWOOM,
        category=TRCategory.HISTORICAL_CANDLE,  # 적절한 카테고리 선택:
                                                 # REALTIME_QUOTE
                                                 # HISTORICAL_CANDLE
                                                 # TICK_DATA
                                                 # OVERSEAS
        description="국내주식 XXX 조회 (REST API)",
        endpoint="/api/dostk/chart",        # Kiwoom은 대부분 동일 endpoint
        method="POST",                      # Kiwoom은 대부분 POST
        implemented=False,                  # 구현 후 True로 변경
        priority="P0",                      # P0(필수), P1(선택), P2(미래)
        documentation_url="https://apiportal.kiwoom.com"
    ),
}
```

**네이밍 규칙**:
- `ka` + 5자리 숫자
- 예: `ka10080`, `ka10079`, `ka10082`

**카테고리 선택 가이드**:
- `REALTIME_QUOTE`: 실시간 시세 조회
- `HISTORICAL_CANDLE`: 과거 분봉/일봉 데이터
- `TICK_DATA`: 체결 데이터 (틱)
- `OVERSEAS`: 해외주식 관련

#### 1.3 USE_CASE_MAPPING 추가

```python
# USE_CASE_MAPPING 딕셔너리에 추가
USE_CASE_MAPPING: Dict[UseCase, Dict[Provider, str]] = {
    # ... 기존 매핑 ...
    
    UseCase.YOUR_USE_CASE_KIWOOM: {
        Provider.KIWOOM: "ka10XXX",
        # KIS는 없을 수 있음 (Kiwoom 전용인 경우)
    },
}
```

---

### Step 2: KiwoomClient 구현

**파일**: `src/api_gateway/hub/clients/kiwoom_client.py`

#### 2.1 _build_headers() OpenAPI+ 매핑 추가 (필요 시)

OpenAPI+ TR ID가 있는 경우 매핑 추가:

```python
    def _build_headers(self, tr_id: str, **kwargs) -> Dict[str, str]:
        """Kiwoom API 헤더 구성 (RFC-008 준수)"""
        # OpenAPI+ TR ID → REST API ID 매핑
        api_id_map = {
            "opt10081": "ka10080",  # 분봉 조회
            "opt10079": "ka10079",  # 틱 조회
            "opt10XXX": "ka10XXX",  # 새 매핑 추가
        }
        api_id = api_id_map.get(tr_id, tr_id)
        
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {self._access_token}",
            "api-id": api_id,  # 매핑된 API ID 사용
            "content-yn": "N",
            "User-Agent": "Mozilla/5.0"
        }
```

#### 2.2 _build_request_body() 파라미터 빌더 추가

```python
    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Kiwoom API 요청 바디 구성 (REST API ka100xx 형식)"""
        
        # ... 기존 API IDs ...
        
        # ka10XXX (설명) - opt10XXX 매핑 포함
        if tr_id in ["ka10XXX", "opt10XXX"]:
            return {
                "stk_cd": params["symbol"],              # 종목코드 (필수)
                "your_param_1": params.get("your_param_1", "default_value"),
                "your_param_2": params.get("your_param_2", ""),
                # 필요한 파라미터 추가
            }
        
        return params
```

**Kiwoom 파라미터 네이밍 규칙** (snake_case):
- `stk_cd`: 종목코드
- `tic_scope`: 틱/분 범위 (1, 3, 5, 10, 30, 60분 등)
- `upd_stkpc_tp`: 수정주가 반영 여부 (0=미반영, 1=반영)
- `inq_strt_dt`: 조회 시작일 (YYYYMMDD)
- `inq_end_dt`: 조회 종료일 (YYYYMMDD)

**파라미터 매핑 전략**:
- `symbol` → `stk_cd`
- `tick_unit` → `tic_scope`
- 사용자 친화적 이름과 공식 파라미터 이름 모두 지원

#### 2.3 _handle_response() 응답 키 매핑 추가 (필요 시)

응답 데이터 키가 다른 경우 매핑 추가:

```python
    async def _handle_response(
        self, response: httpx.Response, tr_id: str
    ) -> Dict[str, Any]:
        """Kiwoom API 응답 처리 (RFC-008 준수)"""
        data = response.json()
        
        # 응답 데이터 키 매핑
        data_key_map = {
            "ka10080": "stk_min_pole_chart_qry",   # 분봉 데이터
            "ka10079": "stk_tic_chart_qry",        # 틱 데이터
            "ka10XXX": "your_response_key_here",   # 새 응답 키 추가
        }
        
        # OpenAPI+ TR ID도 처리
        actual_api_id = tr_id
        if tr_id.startswith("opt"):
            # opt10XXX -> ka10XXX 변환
            api_id_map = {
                "opt10081": "ka10080",
                "opt10079": "ka10079",
                "opt10XXX": "ka10XXX",
            }
            actual_api_id = api_id_map.get(tr_id, tr_id)
        
        data_key = data_key_map.get(actual_api_id, "default_key")
        output_data = data.get(data_key, [])
        
        # 에러 체크
        if not output_data and tr_id not in ["LOGIN", "REG"]:
            if "return_msg" in data and data.get("return_code") != "0000":
                raise APIError(f"Kiwoom API Error: {data.get('return_msg')}")
        
        return {
            "status": "success",
            "provider": "KIWOOM",
            "tr_id": tr_id,
            "data": output_data,
            "message": data.get("return_msg", "Success")
        }
```

---

### Step 3: 테스트 작성

**파일**: `tests/unit/api_gateway/test_kiwoom_client.py`

#### 3.1 파라미터 빌딩 테스트

```python
class TestRequestBodyBuilding:
    """요청 파라미터 빌딩 테스트"""
    
    def test_build_ka10xxx_params(self):
        """ka10XXX 파라미터 빌딩"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        # 1. 기본 파라미터 (symbol만)
        params = client._build_request_body("ka10XXX", {
            "symbol": "005930"
        })
        
        assert params["stk_cd"] == "005930"
        assert params["your_param_1"] == "default_value"
        
        # 2. 전체 파라미터
        params = client._build_request_body("ka10XXX", {
            "symbol": "005930",
            "your_param_1": "custom_value",
            "your_param_2": "param2_value"
        })
        
        assert params["stk_cd"] == "005930"
        assert params["your_param_1"] == "custom_value"
        assert params["your_param_2"] == "param2_value"
```

#### 3.2 OpenAPI+ 매핑 테스트

```python
class TestRequestBodyBuilding:
    """요청 파라미터 빌딩 테스트"""
    
    def test_build_opt10xxx_legacy_mapping(self):
        """opt10XXX (OpenAPI+ TR ID) → ka10XXX 자동 매핑 테스트"""
        client = KiwoomClient(api_key="test", secret_key="test")
        
        params = client._build_request_body("opt10XXX", {
            "symbol": "005930"
        })
        
        assert params["stk_cd"] == "005930"
        # opt10XXX를 사용해도 ka10XXX와 동일한 파라미터 구조
```

#### 3.3 헤더 빌딩 테스트

```python
class TestHeaderBuilding:
    """헤더 빌딩 테스트"""
    
    def test_build_headers_ka10xxx(self):
        """ka10XXX용 헤더 빌딩"""
        client = KiwoomClient(api_key="test_key", secret_key="test_secret")
        client._access_token = "test_token"
        
        headers = client._build_headers("ka10XXX")
        
        assert headers["authorization"] == "Bearer test_token"
        assert headers["api-id"] == "ka10XXX"
        assert headers["content-yn"] == "N"
        assert headers["Content-Type"] == "application/json; charset=UTF-8"
    
    def test_build_headers_opt10xxx_mapping(self):
        """opt10XXX → ka10XXX 자동 매핑 (헤더)"""
        client = KiwoomClient(api_key="test_key", secret_key="test_secret")
        client._access_token = "test_token"
        
        headers = client._build_headers("opt10XXX")
        
        # opt10XXX를 ka10XXX로 매핑해야 함
        assert headers["api-id"] == "ka10XXX"
```

#### 3.4 TR Registry 통합 테스트

```python
class TestTRRegistryIntegration:
    """TR Registry와의 통합 테스트"""
    
    def test_ka10xxx_in_registry(self):
        """TR Registry에 ka10XXX가 등록되어 있는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        spec = get_tr_spec("ka10XXX")
        assert spec is not None
        assert spec.provider.value == "KIWOOM"
        assert spec.implemented is True
    
    def test_ka10xxx_endpoint_matches(self):
        """TR Registry endpoint와 Client get_url_for_tr_id가 일치하는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        client = KiwoomClient(api_key="test", secret_key="test")
        spec = get_tr_spec("ka10XXX")
        
        client_url = client.get_url_for_tr_id("ka10XXX")
        assert spec.endpoint == client_url
```

#### 3.5 테스트 실행

```bash
# 전체 KiwoomClient 테스트 실행
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kiwoom_client.py -v

# 특정 테스트만 실행
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kiwoom_client.py::TestRequestBodyBuilding::test_build_ka10xxx_params -v
```

---

### Step 4: 문서화

**파일**: `docs/specs/api_reference/kiwoom_tr_id_reference.md`

#### 4.1 구현 상태 표 업데이트

```markdown
## 2. 현재 구현 상태

### 2.1 ✅ 구현 완료 (KiwoomClient)

| REST API ID | OpenAPI+ TR ID | 용도 | Endpoint | Method |
|-------------|---------------|------|----------|--------|
| ... | ... | ... | ... | ... |
| `ka10XXX` | `opt10XXX` | 국내주식 XXX 조회 | `/api/dostk/chart` | POST |
```

#### 4.2 API ID 상세 명세 추가

```markdown
### X.X ka10XXX (국내주식 XXX 조회) ✅

**용도**: API ID 사용 목적 상세 설명

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
  "your_param_1": "value1",
  "your_param_2": "value2"
}
```

**Response**:
```json
{
  "your_response_key": [
    {
      "field1": "value1",
      "field2": "value2",
      "cntr_tm": "150000",
      "cur_prc": "70500"
    }
  ],
  "return_msg": "Success",
  "return_code": "0000"
}
```

**OpenAPI+ 매핑**:
- OpenAPI+ TR ID: `opt10XXX`
- REST API에서는 `ka10XXX` 사용 필수
- `opt10XXX`를 헤더에 넣으면 에러 발생 가능

**구현 상태**: ✅ 완료 (2026-01-XX)

**사용처**:
- `your-worker`: 사용 목적 설명

**참고**:
- 조회 가능 기간: YYYYMMDD (예: 20260123)
- 응답 시간 형식: HHMMSS (예: 150000 = 15시 00분 00초)
```

#### 4.3 OpenAPI+ vs REST API 매핑 표 업데이트

```markdown
## 4. OpenAPI+ vs REST API 매핑

| OpenAPI+ TR ID | REST API ID | 용도 | 권장 사용 |
|----------------|-------------|------|----------|
| ... | ... | ... | ... |
| `opt10XXX` | `ka10XXX` | XXX 조회 | REST API (`ka10XXX`) |
```

---

## 📊 구현 완료 후 체크리스트

### 코드 검증
```bash
# TR Registry import 테스트
python3 -c "from src.api_gateway.hub.tr_registry import get_tr_spec; print(get_tr_spec('ka10XXX'))"

# KiwoomClient 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kiwoom_client.py -v

# 전체 API Gateway 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/ -v
```

### TR Registry 검증
- [ ] API ID 형식 검증 통과 (ka + 5자리 숫자)
- [ ] `implemented=True`로 변경
- [ ] UseCase 매핑 정상 동작 확인
- [ ] Implementation stats 업데이트 확인

### 문서 검증
- [ ] Kiwoom TR ID Reference 업데이트 완료
- [ ] OpenAPI+ 매핑 정보 추가
- [ ] 예제 코드 정확성 확인

### 커밋
```bash
git add -A
git commit -m "feat(api-hub): add Kiwoom API ID ka10XXX (description)

Add new Kiwoom API ID ka10XXX for [purpose]:

Implementation:
- Add TRIDSpec to KIWOOM_REGISTRY
- Add OpenAPI+ mapping (opt10XXX -> ka10XXX)
- Add parameter builder in _build_request_body()
- Add response key mapping in _handle_response()

Tests:
- Add parameter building tests
- Add OpenAPI+ mapping tests
- Add TR Registry integration tests

Documentation:
- Update kiwoom_tr_id_reference.md with full specification
- Add OpenAPI+ vs REST API mapping table

Ref: ISSUE-XXX"
```

---

## 🔗 참고 문서

### 공식 API 문서
- [Kiwoom API Portal](https://apiportal.kiwoom.com/)
- [Kiwoom REST API 가이드](https://apiportal.kiwoom.com/intro)

### 내부 문서
- [TR Registry 소스코드](../../src/api_gateway/hub/tr_registry.py)
- [KiwoomClient 소스코드](../../src/api_gateway/hub/clients/kiwoom_client.py)
- [Kiwoom TR ID Reference](../specs/api_reference/kiwoom_tr_id_reference.md)
- [Ground Truth Policy](../governance/ground_truth_policy.md)

### 예제
- [기존 API ID 구현 예제](../../src/api_gateway/hub/clients/kiwoom_client.py#L90-L145)
- [테스트 예제](../../tests/unit/api_gateway/test_kiwoom_client.py)

---

## 💡 팁

### 1. Kiwoom API Portal 사용법
1. [Kiwoom API Portal](https://apiportal.kiwoom.com/) 접속
2. "API 문서" → "REST API" 선택
3. 원하는 API 찾기 (예: "주식 분봉 조회")
4. REST API ID (kaXXXXX), OpenAPI+ TR ID (optXXXXX) 확인
5. Request/Response 스키마 확인

### 2. REST API vs OpenAPI+
- **REST API ID** (kaXXXXX): 최신 방식, 권장
- **OpenAPI+ TR ID** (optXXXXX): 레거시 방식, 호환성 유지
- 항상 REST API ID를 우선 사용
- OpenAPI+ TR ID는 자동 매핑만 지원

### 3. 공통 파라미터
- `stk_cd`: 종목코드 (6자리)
  - 예: `005930` (삼성전자), `035420` (NAVER)
- `tic_scope`: 틱/분 범위
  - `1`, `3`, `5`, `10`, `30`, `60` 등
- `upd_stkpc_tp`: 수정주가 반영
  - `0`: 미반영
  - `1`: 반영

### 4. 응답 데이터 키
- 분봉: `stk_min_pole_chart_qry`
- 틱: `stk_tic_chart_qry`
- 일봉: `stk_day_chart_qry`
- API마다 다를 수 있으므로 공식 문서 확인 필수

### 5. 에러 코드
- `return_code = "0000"`: 성공
- `return_code = "8999"`: 시스템 오류 (Retry with backoff)
- `return_code = "9999"`: 토큰 만료 (Token refresh)

### 6. Rate Limit
- Kiwoom: **10 req/s** (KIS보다 엄격)
- 초과 시 일시적 차단 가능

### 7. Endpoint 특징
- 대부분의 국내주식 API: `/api/dostk/chart`
- 해외주식은 다른 endpoint 사용 가능
- 공식 문서에서 확인 필수

---

**Guide Version**: 1.0  
**Last Updated**: 2026-01-23  
**Maintainer**: Developer Team
