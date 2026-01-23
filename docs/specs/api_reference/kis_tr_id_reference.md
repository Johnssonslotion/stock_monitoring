# KIS API TR ID Reference (Ground Truth)

**Version**: 1.0  
**Last Updated**: 2026-01-23  
**Authority**: KIS OpenAPI Portal (https://apiportal.koreainvestment.com)  
**Status**: API Hub v2 Integration Reference

---

## 1. Overview

본 문서는 API Hub v2가 지원해야 하는 KIS REST API의 TR ID 목록과 파라미터 명세를 정의합니다.

**정책**:
- 모든 TR ID는 KIS 공식 문서에서 검증되어야 함
- API Hub Worker 구현 시 본 문서를 Ground Truth로 사용
- 신규 TR ID 추가 시 본 문서 우선 업데이트

---

## 2. 현재 구현 상태

### 2.1 ✅ 구현 완료 (KISClient)

| TR ID | 용도 | URL Path | Method | 사용처 |
|-------|------|----------|--------|--------|
| `FHKST01010100` | 국내주식 시간별체결가 | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` | GET | - |
| `FHKST01010300` | 국내주식 시간별체결 | `/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion` | GET | `BackfillManager`, `verification-worker` |

### 2.2 ⚠️ 구현 필요

| TR ID | 용도 | URL Path | Method | 우선순위 | 사용처 |
|-------|------|----------|--------|----------|--------|
| `FHKST01010400` | 국내주식 현재가 분봉 | `/uapi/domestic-stock/v1/quotations/inquire-ccnl` | GET | **P0** | `verification-worker` |
| `FHKST03010200` | 국내주식 기간별 분봉 | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` | GET | **P0** | `history-collector`, `KISMinuteCollector` |
| `HHDFS76950200` | 해외주식 기간별 분봉 | `/uapi/overseas-price/v1/quotations/inquire-daily-chartprice` | GET | **P1** | `history-collector` (US) |

---

## 3. TR ID 상세 명세

### 3.1 FHKST01010300 (국내주식 시간별체결) ✅

**용도**: 특정 시간의 틱 데이터 조회 (복구용)

**URL**: `/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion`  
**Method**: GET  
**Authority**: [KIS API Portal - 국내주식시세](https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations)

**Headers**:
```json
{
  "authorization": "Bearer {access_token}",
  "appkey": "{app_key}",
  "appsecret": "{app_secret}",
  "tr_id": "FHKST01010300",
  "custtype": "P"
}
```

**Query Parameters**:
```json
{
  "FID_COND_MRKT_DIV_CODE": "J",       // 시장구분 (J: 주식)
  "FID_INPUT_ISCD": "005930",          // 종목코드
  "FID_INPUT_HOUR_1": "153000"         // 조회시간 (HHMMSS)
}
```

**Response**:
```json
{
  "rt_cd": "0",                         // 성공코드
  "msg1": "정상처리 되었습니다.",
  "output": [
    {
      "stck_cntg_hour": "150000",       // 체결시간 (HHMMSS)
      "stck_prpr": "70500",             // 현재가
      "cntg_vol": "100",                // 체결량
      "acml_vol": "12345678"            // 누적거래량
    }
  ]
}
```

---

### 3.2 FHKST01010400 (국내주식 현재가 분봉) ⚠️ 미구현

**용도**: 실시간 분봉 데이터 조회 (검증용)

**URL**: `/uapi/domestic-stock/v1/quotations/inquire-ccnl`  
**Method**: GET  
**Authority**: [KIS API Portal - 주식현재가체결](https://apiportal.koreainvestment.com/apiservice/apiservice-domestic-stock-quotations)

**Headers**:
```json
{
  "authorization": "Bearer {access_token}",
  "appkey": "{app_key}",
  "appsecret": "{app_secret}",
  "tr_id": "FHKST01010400",
  "custtype": "P"
}
```

**Query Parameters**:
```json
{
  "FID_COND_MRKT_DIV_CODE": "J",       // 시장구분 (J: 주식)
  "FID_INPUT_ISCD": "005930"           // 종목코드
}
```

**Response**:
```json
{
  "rt_cd": "0",
  "output": {
    "stck_prpr": "70500",               // 현재가
    "prdy_vrss": "500",                 // 전일대비
    "acml_vol": "12345678",             // 누적거래량
    "stck_oprc": "70000",               // 시가
    "stck_hgpr": "71000",               // 고가
    "stck_lwpr": "69500"                // 저가
  }
}
```

**사용처**:
- `verification-worker`: 분봉 검증 시 KIS 기준 데이터 조회

---

### 3.3 FHKST03010200 (국내주식 기간별 분봉) ⚠️ 미구현

**용도**: 과거 분봉 데이터 히스토리 조회 (백테스팅/ML)

**URL**: `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice`  
**Method**: GET  
**Authority**: Ground Truth Policy Section 2.2

**Headers**:
```json
{
  "authorization": "Bearer {access_token}",
  "appkey": "{app_key}",
  "appsecret": "{app_secret}",
  "tr_id": "FHKST03010200",
  "custtype": "P"
}
```

**Query Parameters**:
```json
{
  "fid_etc_cls_code": "",              // 기타분류코드 (공백)
  "fid_cond_mrkt_div_code": "J",       // 시장구분 (J: 주식)
  "fid_input_iscd": "005930",          // 종목코드
  "fid_input_hour_1": "153000",        // 시작시간 (HHMMSS)
  "fid_pw_data_incu_yn": "Y"           // 과거데이터포함여부
}
```

**Response**:
```json
{
  "rt_cd": "0",
  "output2": [
    {
      "stck_cntg_hour": "150000",       // 시간 (HHMMSS)
      "stck_prpr": "70500",             // 현재가
      "cntg_vol": "1000",               // 체결량
      "acml_vol": "12345678",           // 누적거래량
      "stck_oprc": "70000",             // 시가
      "stck_hgpr": "70800",             // 고가
      "stck_lwpr": "69900"              // 저가
    }
  ]
}
```

**Pagination**:
- `fid_input_hour_1`을 이전 페이지 마지막 시간으로 설정하여 역방향 페이징
- `output2` 배열이 빈 배열일 때까지 반복

**사용처**:
- `history-collector`: 과거 분봉 히스토리 수집
- `KISMinuteCollector`: 검증용 분봉 데이터 수집

---

### 3.4 HHDFS76950200 (해외주식 기간별 분봉) ⚠️ 미구현

**용도**: 미국 주식 과거 분봉 데이터 조회

**URL**: `/uapi/overseas-price/v1/quotations/inquire-daily-chartprice`  
**Method**: GET  
**Authority**: [KIS API Portal - 해외주식시세](https://apiportal.koreainvestment.com/apiservice/apiservice-overseas-price)

**Headers**:
```json
{
  "authorization": "Bearer {access_token}",
  "appkey": "{app_key}",
  "appsecret": "{app_secret}",
  "tr_id": "HHDFS76950200",
  "custtype": "P"
}
```

**Query Parameters**:
```json
{
  "AUTH": "",                           // 공란
  "EXCD": "NAS",                        // 거래소코드 (NAS: 나스닥, NYS: 뉴욕)
  "SYMB": "AAPL",                       // 종목코드
  "GUBN": "0",                          // 기간분류 (0: 일, 1: 주, 2: 월)
  "BYMD": "20260101",                   // 조회시작일자 (YYYYMMDD)
  "MODP": "1"                           // 수정주가반영여부
}
```

**Response**:
```json
{
  "rt_cd": "0",
  "output2": [
    {
      "xymd": "20260120",               // 일자
      "clos": "150.25",                 // 종가
      "open": "149.50",                 // 시가
      "high": "151.00",                 // 고가
      "low": "149.00",                  // 저가
      "tvol": "50000000"                // 거래량
    }
  ]
}
```

**사용처**:
- `history-collector`: 미국 주식 과거 데이터 수집

---

## 4. Rate Limit (Ground Truth)

| Provider | Rate Limit | Authority |
|----------|------------|-----------|
| KIS | **20 req/s** | Ground Truth Policy Section 8.1 |

**Note**: 공식 문서는 30 req/s를 명시하나, 실제 운영에서 20 req/s로 제한됨 (Ground Truth Policy 기준)

---

## 5. Error Codes

### 5.1 공통 에러

| rt_cd | msg1 | 의미 | 조치 |
|-------|------|------|------|
| `0` | 정상처리 | 성공 | - |
| `-1` | 시스템 오류 | 서버 장애 | Retry with backoff |
| `EGW00123` | 초당 거래건수 초과 | Rate Limit | Wait and retry |
| `EGW00201` | 토큰 만료 | Auth 실패 | Token refresh |

### 5.2 데이터 없음

- `rt_cd = "0"` 이지만 `output` 또는 `output2` 배열이 빈 경우
- 정상적인 상태 (해당 시간/종목에 데이터 없음)

---

## 6. Schema Discovery (실제 API 응답 수집)

**목적**: 각 TR ID별 실제 API 응답 구조를 수집하여 구현 정확도 향상

**테스트 파일**: `tests/integration/test_api_schema_discovery.py`

**실행 방법**:
```bash
# 모든 TR ID 스키마 수집
PYTHONPATH=. poetry run pytest tests/integration/test_api_schema_discovery.py::test_discover_all_schemas -v -s -m manual
```

**출력**:
- JSON 스키마 파일: `docs/specs/api_reference/schemas/{provider}_{tr_id}_schema.json`
- 자동 생성 문서: `docs/specs/api_reference/schemas/README.md`

**상세 가이드**: [API Schema Discovery Guide](../../operations/testing/api_schema_discovery_guide.md)

---

## 7. Implementation Checklist

### Phase 0: 스키마 수집 (선행 작업)
- [ ] Schema Discovery 테스트 실행
- [ ] 실제 API 응답 구조 확인
- [ ] 에러 케이스 파악

### Phase 1: KISClient 확장
- [ ] `TR_URL_MAP`에 3개 TR ID 추가
- [ ] `_build_request_body()` 각 TR ID별 파라미터 구조 구현 (스키마 참조)
- [ ] `GET_TRS` 세트 업데이트
- [ ] `_handle_response()` TR ID별 응답 구조 처리 (스키마 참조)

### Phase 2: 테스트
- [ ] Unit Test: 각 TR ID별 파라미터 생성 검증
- [ ] Integration Test: 수집된 스키마 기반 Fixture 테스트
- [ ] Manual Test: Sandbox 환경 실제 API 호출

### Phase 3: 문서화
- [ ] `api_hub_v2_overview.md` 업데이트
- [ ] Test Registry 업데이트
- [ ] BACKLOG.md 업데이트

---

## 8. 관련 문서

### 정책 및 명세
- **Ground Truth Policy**: `docs/governance/ground_truth_policy.md` Section 2.2
- **KIS Endpoint Map**: `docs/specs/api_reference/kis_endpoint_map.md`
- **API Hub Overview**: `docs/specs/api_hub_v2_overview.md`
- **ISSUE-041**: `docs/issues/ISSUE-041.md`

### 테스트 및 스키마
- **Schema Discovery Guide**: `docs/operations/testing/api_schema_discovery_guide.md` ⭐
- **Schema Discovery Test**: `tests/integration/test_api_schema_discovery.py`
- **Collected Schemas**: `docs/specs/api_reference/schemas/` (실행 후 생성)

---

**Document Owner**: Developer Persona  
**Review Cycle**: Per TR ID addition  
**Next Review**: Upon Schema Discovery completion
