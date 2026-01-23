# KIS TR ID 추가 가이드

한국투자증권(KIS) REST API의 새로운 TR ID를 API Hub v2에 추가하는 방법을 단계별로 안내합니다.

---

## 📋 체크리스트

### Phase 1: 사전 조사
- [ ] [KIS API Portal](https://apiportal.koreainvestment.com/)에서 TR ID 확인
- [ ] Endpoint URL 확인
- [ ] Request Parameters (FID_XXX 형식) 확인
- [ ] Response Schema 확인
- [ ] HTTP Method 확인 (대부분 GET)
- [ ] 사용 목적(UseCase) 정의

### Phase 2: TR Registry 등록
- [ ] `src/api_gateway/hub/tr_registry.py` 업데이트
- [ ] TR ID 네이밍 규칙 준수 (대문자 영숫자 10+ 글자)
- [ ] UseCase enum 추가 (필요 시)
- [ ] TRIDSpec 정의 추가

### Phase 3: KISClient 구현
- [ ] `src/api_gateway/hub/clients/kis_client.py` 업데이트
- [ ] `TR_URL_MAP` 딕셔너리에 URL 매핑 추가
- [ ] `_build_request_body()` 파라미터 빌더 추가
- [ ] `GET_TRS` set에 TR ID 추가 (GET method인 경우)

### Phase 4: 테스트 작성
- [ ] `tests/unit/api_gateway/test_kis_client.py` 업데이트
- [ ] Unit Test: 파라미터 빌딩 검증
- [ ] Unit Test: URL 매핑 검증
- [ ] Unit Test: TR Registry 통합 검증

### Phase 5: 문서화
- [ ] `docs/specs/api_reference/kis_tr_id_reference.md` 업데이트
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
    YOUR_USE_CASE_KIS = "YOUR_USE_CASE_KIS"  # 예: DAILY_CANDLE_KIS
```

#### 1.2 KIS_REGISTRY에 TRIDSpec 추가

```python
# KIS_REGISTRY 딕셔너리에 추가
KIS_REGISTRY: Dict[str, TRIDSpec] = {
    # ... 기존 TR IDs ...
    
    "FHKSTXXXXXXXX": TRIDSpec(
        tr_id="FHKSTXXXXXXXX",              # 예: FHKST01010500
        provider=Provider.KIS,
        category=TRCategory.HISTORICAL_CANDLE,  # 적절한 카테고리 선택:
                                                 # REALTIME_QUOTE
                                                 # HISTORICAL_CANDLE
                                                 # TICK_DATA
                                                 # OVERSEAS
        description="국내주식 XXX 조회",
        endpoint="/uapi/domestic-stock/v1/quotations/your-endpoint",
        method="GET",                       # 대부분 GET, 드물게 POST
        implemented=False,                  # 구현 후 True로 변경
        priority="P0",                      # P0(필수), P1(선택), P2(미래)
        documentation_url="https://apiportal.koreainvestment.com/apiservice/..."
    ),
}
```

**네이밍 규칙**:
- 대문자 영숫자 조합
- 최소 10글자 이상
- 예: `FHKST01010100`, `HHDFS76950200`

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
    
    UseCase.YOUR_USE_CASE_KIS: {
        Provider.KIS: "FHKSTXXXXXXXX",
        # Kiwoom은 없을 수 있음 (KIS 전용인 경우)
    },
}
```

---

### Step 2: KISClient 구현

**파일**: `src/api_gateway/hub/clients/kis_client.py`

#### 2.1 TR_URL_MAP 업데이트

```python
class KISClient(BaseAPIClient):
    """한국투자증권 REST API 클라이언트"""
    
    TR_URL_MAP = {
        # ... 기존 매핑 ...
        "FHKST01010100": "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
        "FHKST01010300": "/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion",
        
        # 새 TR ID 추가
        "FHKSTXXXXXXXX": "/uapi/domestic-stock/v1/quotations/your-endpoint",
    }
```

#### 2.2 GET_TRS 업데이트 (GET method인 경우)

```python
    GET_TRS = {
        "FHKST01010100",
        "FHKST01010300",
        "FHKST01010400",
        "FHKST03010200",
        "HHDFS76950200",
        "FHKSTXXXXXXXX",  # GET method 사용하는 경우만 추가
    }
```

#### 2.3 _build_request_body() 파라미터 빌더 추가

```python
    def _build_request_body(
        self, tr_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """KIS API 요청 파라미터 구성"""
        
        # ... 기존 TR IDs ...
        
        # FHKSTXXXXXXXX (설명)
        if tr_id == "FHKSTXXXXXXXX":
            return {
                # 필수 파라미터
                "FID_COND_MRKT_DIV_CODE": params.get("FID_COND_MRKT_DIV_CODE", "J"),
                "FID_INPUT_ISCD": params.get("symbol") or params.get("FID_INPUT_ISCD"),
                
                # TR ID별 특수 파라미터
                "FID_INPUT_DATE_1": params.get("date") or params.get("FID_INPUT_DATE_1", ""),
                "FID_PERIOD_DIV_CODE": params.get("period") or params.get("FID_PERIOD_DIV_CODE", "D"),
                
                # 옵션 파라미터 (기본값 설정)
                "FID_ORG_ADJ_PRC": params.get("FID_ORG_ADJ_PRC", "0"),
            }
        
        return params
```

**KIS 파라미터 네이밍 규칙**:
- `FID_COND_MRKT_DIV_CODE`: 시장 구분 (J=주식, ETF/ETN 등)
- `FID_INPUT_ISCD`: 종목코드
- `FID_INPUT_DATE_1`: 조회 시작일
- `FID_PERIOD_DIV_CODE`: 기간 구분 (D=일, W=주, M=월)
- `FID_ORG_ADJ_PRC`: 수정주가 반영 여부 (0=미반영, 1=반영)

**파라미터 매핑 전략**:
- `symbol` → `FID_INPUT_ISCD`
- `date` → `FID_INPUT_DATE_1`
- `period` → `FID_PERIOD_DIV_CODE`
- 사용자 친화적 이름과 공식 FID 이름 모두 지원

---

### Step 3: 테스트 작성

**파일**: `tests/unit/api_gateway/test_kis_client.py`

#### 3.1 파라미터 빌딩 테스트

```python
class TestRequestBodyBuilding:
    """요청 파라미터 빌딩 테스트"""
    
    def test_build_fhkstxxxxxxxx_params(self):
        """FHKSTXXXXXXXX 파라미터 빌딩"""
        client = KISClient(app_key="test", app_secret="test")
        
        # 1. 간단한 파라미터 (symbol만)
        params = client._build_request_body("FHKSTXXXXXXXX", {
            "symbol": "005930"
        })
        
        assert params["FID_COND_MRKT_DIV_CODE"] == "J"
        assert params["FID_INPUT_ISCD"] == "005930"
        
        # 2. 사용자 친화적 파라미터 사용
        params = client._build_request_body("FHKSTXXXXXXXX", {
            "symbol": "005930",
            "date": "20260123",
            "period": "W"
        })
        
        assert params["FID_INPUT_ISCD"] == "005930"
        assert params["FID_INPUT_DATE_1"] == "20260123"
        assert params["FID_PERIOD_DIV_CODE"] == "W"
        
        # 3. 공식 FID 파라미터 직접 사용
        params = client._build_request_body("FHKSTXXXXXXXX", {
            "FID_INPUT_ISCD": "035420",
            "FID_INPUT_DATE_1": "20260101",
            "FID_PERIOD_DIV_CODE": "M"
        })
        
        assert params["FID_INPUT_ISCD"] == "035420"
        assert params["FID_INPUT_DATE_1"] == "20260101"
        assert params["FID_PERIOD_DIV_CODE"] == "M"
```

#### 3.2 URL 매핑 테스트

```python
class TestTRURLMapping:
    """TR ID → URL 매핑 테스트"""
    
    def test_fhkstxxxxxxxx_in_url_map(self):
        """FHKSTXXXXXXXX가 TR_URL_MAP에 있는지 확인"""
        client = KISClient(app_key="test", app_secret="test")
        
        assert "FHKSTXXXXXXXX" in client.TR_URL_MAP
        
    def test_get_url_for_fhkstxxxxxxxx(self):
        """FHKSTXXXXXXXX URL 조회"""
        client = KISClient(app_key="test", app_secret="test")
        
        url = client.get_url_for_tr_id("FHKSTXXXXXXXX")
        assert url == "/uapi/domestic-stock/v1/quotations/your-endpoint"
```

#### 3.3 HTTP Method 테스트

```python
class TestMethodSelection:
    """HTTP Method 자동 선택 테스트"""
    
    def test_fhkstxxxxxxxx_in_get_trs(self):
        """FHKSTXXXXXXXX가 GET_TRS에 있는지 확인 (GET method인 경우)"""
        client = KISClient(app_key="test", app_secret="test")
        
        assert "FHKSTXXXXXXXX" in client.GET_TRS
```

#### 3.4 TR Registry 통합 테스트

```python
class TestTRRegistryIntegration:
    """TR Registry와의 통합 테스트"""
    
    def test_fhkstxxxxxxxx_in_registry(self):
        """TR Registry에 FHKSTXXXXXXXX가 등록되어 있는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        spec = get_tr_spec("FHKSTXXXXXXXX")
        assert spec is not None
        assert spec.provider.value == "KIS"
        assert spec.implemented is True
        
    def test_fhkstxxxxxxxx_endpoint_matches(self):
        """TR Registry endpoint와 Client URL_MAP이 일치하는지 확인"""
        from src.api_gateway.hub.tr_registry import get_tr_spec
        
        client = KISClient(app_key="test", app_secret="test")
        spec = get_tr_spec("FHKSTXXXXXXXX")
        
        assert spec.endpoint == client.TR_URL_MAP["FHKSTXXXXXXXX"]
```

#### 3.5 테스트 실행

```bash
# 전체 KISClient 테스트 실행
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kis_client.py -v

# 특정 테스트만 실행
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kis_client.py::TestRequestBodyBuilding::test_build_fhkstxxxxxxxx_params -v
```

---

### Step 4: 문서화

**파일**: `docs/specs/api_reference/kis_tr_id_reference.md`

#### 4.1 구현 상태 표 업데이트

```markdown
## 2. 현재 구현 상태

### 2.1 ✅ 구현 완료 (KISClient)

| TR ID | 용도 | Endpoint | Method |
|-------|------|----------|--------|
| ... | ... | ... | ... |
| `FHKSTXXXXXXXX` | 국내주식 XXX 조회 | `/uapi/domestic-stock/v1/quotations/your-endpoint` | GET |
```

#### 4.2 TR ID 상세 명세 추가

```markdown
### X.X FHKSTXXXXXXXX (국내주식 XXX 조회) ✅

**용도**: TR ID 사용 목적 상세 설명

**URL**: `https://openapi.koreainvestment.com/uapi/domestic-stock/v1/quotations/your-endpoint`  
**Method**: GET  
**Authority**: [KIS API Portal - 국내주식시세](https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations)

**Headers**:
```json
{
  "authorization": "Bearer {access_token}",
  "appkey": "{app_key}",
  "appsecret": "{app_secret}",
  "tr_id": "FHKSTXXXXXXXX",
  "custtype": "P"
}
```

**Query Parameters**:
```json
{
  "FID_COND_MRKT_DIV_CODE": "J",
  "FID_INPUT_ISCD": "005930",
  "FID_INPUT_DATE_1": "20260123",
  "FID_PERIOD_DIV_CODE": "D",
  "FID_ORG_ADJ_PRC": "0"
}
```

**Response**:
```json
{
  "output": [
    {
      "stck_bsop_date": "20260123",
      "stck_clpr": "70500",
      "stck_oprc": "70000",
      "stck_hgpr": "70800",
      "stck_lwpr": "69900",
      "acml_vol": "12345678"
    }
  ],
  "rt_cd": "0",
  "msg_cd": "MCA00000",
  "msg1": "정상처리 되었습니다."
}
```

**구현 상태**: ✅ 완료 (2026-01-XX)

**사용처**:
- `your-worker`: 사용 목적 설명

**참고**:
- 조회 가능 기간: YYYYMMDD (예: 20260123)
- 수정주가 반영 옵션: 0=미반영, 1=반영
- 시장 구분 코드: J=주식, ETF, ETN 등
```

---

## 📊 구현 완료 후 체크리스트

### 코드 검증
```bash
# TR Registry import 테스트
python3 -c "from src.api_gateway.hub.tr_registry import get_tr_spec; print(get_tr_spec('FHKSTXXXXXXXX'))"

# KISClient 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/test_kis_client.py -v

# 전체 API Gateway 테스트
PYTHONPATH=. poetry run pytest tests/unit/api_gateway/ -v
```

### TR Registry 검증
- [ ] TR ID 형식 검증 통과 (대문자 영숫자 10+ 글자)
- [ ] `implemented=True`로 변경
- [ ] UseCase 매핑 정상 동작 확인
- [ ] Implementation stats 업데이트 확인

### 문서 검증
- [ ] KIS TR ID Reference 업데이트 완료
- [ ] 예제 코드 정확성 확인
- [ ] API Portal 링크 정상 동작 확인

### 커밋
```bash
git add -A
git commit -m "feat(api-hub): add KIS TR ID FHKSTXXXXXXXX (description)

Add new KIS TR ID FHKSTXXXXXXXX for [purpose]:

Implementation:
- Add TRIDSpec to KIS_REGISTRY
- Add URL mapping to KISClient.TR_URL_MAP
- Add parameter builder in _build_request_body()
- Add to GET_TRS set

Tests:
- Add parameter building tests
- Add URL mapping tests
- Add TR Registry integration tests

Documentation:
- Update kis_tr_id_reference.md with full specification

Ref: ISSUE-XXX"
```

---

## 🔗 참고 문서

### 공식 API 문서
- [KIS API Portal](https://apiportal.koreainvestment.com/)
- [국내주식시세 API](https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations)
- [해외주식시세 API](https://apiportal.koreainvestment.com/apiservice/apiservice-overseas-stock)

### 내부 문서
- [TR Registry 소스코드](../../src/api_gateway/hub/tr_registry.py)
- [KISClient 소스코드](../../src/api_gateway/hub/clients/kis_client.py)
- [KIS TR ID Reference](../specs/api_reference/kis_tr_id_reference.md)
- [Ground Truth Policy](../governance/ground_truth_policy.md)

### 예제
- [기존 TR ID 구현 예제](../../src/api_gateway/hub/clients/kis_client.py#L80-L180)
- [테스트 예제](../../tests/unit/api_gateway/test_kis_client.py)

---

## 💡 팁

### 1. KIS 공식 문서 찾기
1. [KIS API Portal](https://apiportal.koreainvestment.com/) 접속
2. "API 서비스" → "국내주식" 또는 "해외주식" 선택
3. 원하는 API 찾기 (예: "주식현재가 시세")
4. TR ID, Endpoint, Parameters 확인

### 2. FID 파라미터 이해
- `FID_COND_MRKT_DIV_CODE`: 시장 구분
  - `J`: 주식/ETF/ETN
  - `W`: ELW
- `FID_INPUT_ISCD`: 종목코드 (6자리)
- `FID_INPUT_DATE_1`: 시작일 (YYYYMMDD)
- `FID_INPUT_DATE_2`: 종료일 (YYYYMMDD)
- `FID_PERIOD_DIV_CODE`: 기간 구분
  - `D`: 일봉
  - `W`: 주봉
  - `M`: 월봉
- `FID_ORG_ADJ_PRC`: 수정주가 반영
  - `0`: 미반영
  - `1`: 반영

### 3. HTTP Method 선택
- **GET**: 대부분의 조회 API (시세, 잔고, 체결 등)
- **POST**: 주문 실행 API (매수, 매도, 정정, 취소)

### 4. 응답 필드 이해
- `output`: 실제 데이터 배열
- `rt_cd`: 응답 코드 (0=성공)
- `msg_cd`: 메시지 코드
- `msg1`: 응답 메시지

### 5. 테스트 데이터
- 종목코드: `005930` (삼성전자), `035420` (NAVER)
- 날짜: `20260123` (YYYYMMDD 형식)

---

**Guide Version**: 1.0  
**Last Updated**: 2026-01-23  
**Maintainer**: Developer Team
