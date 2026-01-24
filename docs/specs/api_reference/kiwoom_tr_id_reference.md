# Kiwoom API TR ID Reference (Ground Truth)

**Version**: 1.0  
**Last Updated**: 2026-01-23  
**Authority**: Kiwoom OpenAPI Portal (https://apiportal.kiwoom.com)  
**Status**: API Hub v2 Integration Reference

---

## 1. Overview

본 문서는 API Hub v2가 지원해야 하는 Kiwoom REST API의 API ID 목록과 파라미터 명세를 정의합니다.

**중요**: Kiwoom은 OpenAPI+ (TR ID)와 REST API (API ID)를 모두 제공하나, REST API 우선 사용.

**정책**:
- 모든 API ID는 Kiwoom 공식 문서에서 검증되어야 함
- OpenAPI+ TR ID → REST API ID 매핑 필수
- API Hub Worker 구현 시 본 문서를 Ground Truth로 사용

---

## 2. 현재 구현 상태

### 2.1 ✅ 구현 완료 (KiwoomClient)

| REST API ID | OpenAPI+ TR ID | 용도 | Endpoint | Method |
|-------------|---------------|------|----------|--------|
| `ka10080` | `opt10081` | 국내주식 분봉 조회 | `/api/dostk/chart` | POST |
| `ka10079` | `opt10079` | 국내주식 틱 조회 | `/api/dostk/chart` | POST |

### 2.2 ⚠️ 구현 필요 (또는 검증 필요)

**없음** - 모든 필수 TR ID 구현 완료 (100% coverage)

**Note**: ~~`KIS_CL_PBC_04020`는 코드에서 사용 중이나 Kiwoom 공식 문서에서 확인 불가.~~ **[FIXED 2026-01-23]** `verification-worker`에서 `ka10080`으로 수정 완료.

---

## 3. TR ID 상세 명세

### 3.1 ka10080 (국내주식 분봉 조회) ✅

**용도**: 과거 분봉 데이터 조회 (검증/히스토리)

**URL**: `https://api.kiwoom.com/api/dostk/chart`  
**Method**: POST  
**Authority**: [Kiwoom Chart API Spec](../../specs/kiwoom-chart-api.md)

**Headers**:
```json
{
  "Content-Type": "application/json; charset=UTF-8",
  "authorization": "Bearer {access_token}",
  "api-id": "ka10080",
  "content-yn": "N",
  "User-Agent": "Mozilla/5.0"
}
```

**Body**:
```json
{
  "stk_cd": "005930",                   // 종목코드
  "tic_scope": "1",                     // 틱범위 (1: 1분, 3: 3분...)
  "upd_stkpc_tp": "1"                   // 수정주가반영 (0: 미반영, 1: 반영)
}
```

**Response**:
```json
{
  "stk_min_pole_chart_qry": [
    {
      "cntr_tm": "150000",              // 시간 (HHMMSS)
      "cur_prc": "70500",               // 현재가
      "trde_qty": "1000",               // 거래량
      "open_pric": "70000",             // 시가
      "high_pric": "70800",             // 고가
      "low_pric": "69900",              // 저가
      "pred_pre": "500"                 // 전일대비
    }
  ],
  "return_msg": "Success",
  "return_code": "0000"
}
```

**OpenAPI+ 매핑**:
- OpenAPI+ TR ID: `opt10081` (분봉)
- REST API에서는 `ka10080` 사용 필수
- `opt10081`을 헤더에 넣으면 에러 발생 가능

**사용처**:
- `history-collector`: 과거 분봉 히스토리 수집
- `verification-worker`: 검증용 분봉 데이터 조회

---

### 3.2 ka10079 (국내주식 틱 조회) ✅

**용도**: 과거 틱 데이터 조회

**URL**: `https://api.kiwoom.com/api/dostk/chart`  
**Method**: POST  
**Authority**: [Kiwoom Tick Chart Spec](kiwoom-chart-api.md)

**Headers**:
```json
{
  "Content-Type": "application/json; charset=UTF-8",
  "authorization": "Bearer {access_token}",
  "api-id": "ka10079",
  "content-yn": "N",
  "User-Agent": "Mozilla/5.0"
}
```

**Body**:
```json
{
  "stk_cd": "005930",                   // 종목코드
  "tic_scope": "1",                     // 틱범위 (1: 1틱, 10: 10틱...)
  "upd_stkpc_tp": "0"                   // 수정주가반영 (0: 미반영)
}
```

**Response**:
```json
{
  "stk_tic_chart_qry": [
    {
      "cntr_tm": "150000",              // 체결시간 (HHMMSS)
      "cur_prc": "70500",               // 체결가
      "trde_qty": "100",                // 체결량
      "pred_pre": "500"                 // 전일대비
    }
  ]
}
```

**OpenAPI+ 매핑**:
- OpenAPI+ TR ID: `opt10079` (틱)
- REST API에서는 `ka10079` 사용

**사용처**:
- 현재 미사용 (향후 필요 시 사용 가능)
- KiwoomClient에서 구현 완료 (2026-01-23)

---

### 3.3 KIS_CL_PBC_04020 ✅ 해결됨

**Status**: **RESOLVED [2026-01-23]** - Kiwoom 공식 문서에서 확인 불가한 잘못된 TR ID였음

**이전 코드 사용처**:
```python
# src/verification/worker.py:120 (BEFORE FIX)
API_TR_MAPPING = {
    "KIWOOM": {
        "minute_candle": "KIS_CL_PBC_04020",  # ❌ 잘못된 ID
    }
}
```

**수정 후**:
```python
# src/verification/worker.py:120 (AFTER FIX - 2026-01-23)
API_TR_MAPPING = {
    "KIWOOM": {
        "minute_candle": "ka10080",  # ✅ 올바른 REST API ID
    }
}
```

**결론**:
- ❌ `KIS_CL_PBC_04020`는 존재하지 않는 TR ID였음
- ✅ 올바른 ID는 `ka10080` (REST API ID)
- ✅ 2026-01-23 수정 완료 (`verification-worker`)

---

## 4. OpenAPI+ vs REST API 매핑

| OpenAPI+ TR ID | REST API ID | 용도 | 권장 사용 |
|----------------|-------------|------|----------|
| `opt10081` | `ka10080` | 분봉 조회 | REST API (`ka10080`) |
| `opt10079` | `ka10079` | 틱 조회 | REST API (`ka10079`) |
| `opt10080` | N/A | (구버전) | **사용 금지** |

**중요**: REST API (`ka100xx`)를 우선 사용. OpenAPI+ TR ID는 헤더에 사용하지 말 것.

---

## 5. Rate Limit (Ground Truth)

| Provider | Rate Limit | Authority |
|----------|------------|-----------|
| Kiwoom | **10 req/s** | Ground Truth Policy Section 8.1 |

**Note**: KIS보다 엄격한 제한 (10 vs 20 req/s)

---

## 6. Error Codes

### 6.1 공통 에러

| return_code | return_msg | 의미 | 조치 |
|-------------|-----------|------|------|
| `0000` | Success | 성공 | - |
| `8999` | 시스템 오류 | 서버 장애 | Retry with backoff |
| `9999` | 토큰 만료 | Auth 실패 | Token refresh |

### 6.2 데이터 없음

- `return_code = "0000"` 이지만 `stk_min_pole_chart_qry` 배열이 빈 경우
- 정상적인 상태 (해당 시간/종목에 데이터 없음)

---

## 7. KiwoomClient 구현 체크리스트

### Phase 1: 현재 상태 확인
- [x] `ka10080` 구현 완료
- [x] `ka10079` 구현 완료 (2026-01-23) - 100% coverage 달성
- [x] ~~`KIS_CL_PBC_04020` 정체 확인~~ → **[RESOLVED 2026-01-23]** 존재하지 않는 ID였음

### Phase 2: 코드 정리
- [x] ~~`verification-worker`의 `KIS_CL_PBC_04020` → `ka10080`으로 변경~~ → **[DONE 2026-01-23]**
- [x] `ka10079` 구현 완료 (KiwoomClient) → **[DONE 2026-01-23]**
- [ ] 실제 API 호출 테스트로 검증
- [x] 불필요한 TR ID 제거

### Phase 3: 테스트
- [x] Unit Test: `ka10080` 파라미터 생성 검증 → **[DONE 2026-01-23]**
- [x] Unit Test: `ka10079` 파라미터 생성 검증 → **[DONE 2026-01-23]**
- [x] Unit Test: TR Registry 통합 검증 (66 tests PASSED) → **[DONE 2026-01-23]**
- [ ] Integration Test: Fixture 기반 응답 파싱 검증
- [ ] Manual Test: Sandbox 환경 실제 API 호출

---

## 8. 관련 문서

- **Ground Truth Policy**: `docs/governance/ground_truth_policy.md` Section 2.2
- **Kiwoom Chart API Spec**: `docs/specs/kiwoom-chart-api.md`
- **Kiwoom FID Mappings**: `docs/specs/api_reference/kiwoom_fid_mappings.md` (WebSocket 전용)
- **API Hub Overview**: `docs/specs/api_hub_v2_overview.md`
- **ISSUE-041**: `docs/issues/ISSUE-041.md`

---

**Document Owner**: Developer Persona  
**Review Cycle**: Per API ID addition  
**Next Review**: ~~Upon `KIS_CL_PBC_04020` 정체 확인 후~~ → **Next schema discovery test execution**

---

## 9. Action Items (Immediate)

### ✅ Completed
1. ~~**`KIS_CL_PBC_04020` 정체 확인**~~ → **[RESOLVED 2026-01-23]**
   - ✅ Kiwoom API 문서 재확인 완료
   - ✅ 존재하지 않는 TR ID로 확인
   - ✅ 올바른 ID는 `ka10080`

2. ~~**verification-worker 코드 수정**~~ → **[DONE 2026-01-23]**
   ```python
   # Before
   API_TR_MAPPING = {
       "KIWOOM": {
           "minute_candle": "KIS_CL_PBC_04020",  # ❌ UNKNOWN
       }
   }
   
   # After (수정 완료)
   API_TR_MAPPING = {
       "KIWOOM": {
           "minute_candle": "ka10080",  # ✅ Official REST API ID
       }
   }
   ```

### 🟢 Completed (2026-01-23)
3. **KiwoomClient 확장 완료**:
   - ✅ `ka10079` (틱 조회) 구현 완료
   - ✅ 17개 단위 테스트 작성 및 통과
   - ✅ 100% TR ID coverage 달성 (2/2)
