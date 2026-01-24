# API Schema Discovery Guide

**Test File**: `tests/integration/test_api_schema_discovery.py`  
**Purpose**: 각 증권사 REST API의 실제 응답 스키마를 수집하여 자동 문서화

---

## 1. 개요

본 테스트는 다음을 수행합니다:

1. **실제 API 호출**: API Hub v2를 통해 각 TR ID별 실제 API 호출
2. **응답 수집**: 실제 API 응답 데이터 수집
3. **스키마 분석**: 응답 구조 자동 분석 (type, fields, examples)
4. **자동 문서화**: JSON 스키마 파일 + Markdown 문서 자동 생성

---

## 2. 전제조건

### 2.1 환경변수 설정

```bash
# KIS API
export KIS_APP_KEY="your_kis_app_key"
export KIS_APP_SECRET="your_kis_app_secret"
export KIS_BASE_URL="https://openapi.koreainvestment.com:9443"

# Kiwoom API
export KIWOOM_API_KEY="your_kiwoom_api_key"
export KIWOOM_SECRET_KEY="your_kiwoom_secret_key"
export KIWOOM_REST_API_URL="https://api.kiwoom.com"
```

### 2.2 인프라 실행

```bash
# Redis 실행
docker-compose up -d redis

# Redis Gatekeeper 실행 (Rate Limiter)
docker-compose up -d redis-gatekeeper

# API Hub Worker 실행 (Real API Mode)
ENABLE_MOCK=false docker-compose up -d gateway-worker-real
```

### 2.3 확인

```bash
# Redis 연결 확인
redis-cli ping  # 응답: PONG

# Gateway Worker 확인
docker logs gateway-worker-real  # "✅ RestApiWorker setup completed" 확인
```

---

## 3. 테스트 대상 TR ID

### 3.1 KIS (한국투자증권)

| TR ID | Description | Priority |
|-------|-------------|----------|
| `FHKST01010300` | 국내주식 시간별체결 (틱) | P0 |
| `FHKST01010400` | 국내주식 현재가 분봉 | P0 |
| `FHKST03010200` | 국내주식 기간별 분봉 | P0 |
| `HHDFS76950200` | 해외주식 기간별 분봉 | P1 |

### 3.2 Kiwoom (키움증권)

| API ID | Description | Priority |
|--------|-------------|----------|
| `ka10080` | 국내주식 분봉 조회 | P0 |
| `ka10079` | 국내주식 틱 조회 | P1 |

---

## 4. 실행 방법

### 4.1 전체 스키마 수집

```bash
# 모든 TR ID 스키마 수집
PYTHONPATH=. poetry run pytest tests/integration/test_api_schema_discovery.py::test_discover_all_schemas -v -s -m manual
```

**예상 소요 시간**: 약 30-60초 (6개 API × 5초)

**출력 예시**:
```
================================================================================
API Schema Discovery Test
================================================================================

[1/6] Testing KIS - FHKST01010300
Description: 국내주식 시간별체결 (틱 데이터)
Params: {
  "symbol": "005930",
  "time": "150000"
}
✅ SUCCESS
Response keys: ['rt_cd', 'msg1', 'output']
✅ Schema saved: docs/specs/api_reference/schemas/kis_fhkst01010300_schema.json

[2/6] Testing KIS - FHKST01010400
...

================================================================================
Test Results Summary
================================================================================

✅ KIS      FHKST01010300        - SUCCESS
✅ KIS      FHKST01010400        - SUCCESS
✅ KIS      FHKST03010200        - SUCCESS
✅ KIS      HHDFS76950200        - SUCCESS
✅ KIWOOM   ka10080              - SUCCESS
❌ KIWOOM   ka10079              - FAILED (Rate Limit)

📊 Success Rate: 5/6
📄 Documentation generated: docs/specs/api_reference/schemas/README.md
```

### 4.2 단일 TR ID 테스트 (디버깅용)

```bash
# KIS 틱 데이터만 테스트
PYTHONPATH=. poetry run pytest tests/integration/test_api_schema_discovery.py::test_single_schema_kis_tick -v -s -m manual
```

---

## 5. 출력 파일

### 5.1 스키마 파일 (JSON)

**위치**: `docs/specs/api_reference/schemas/`

**파일명 형식**: `{provider}_{tr_id}_schema.json`

**예시**: `kis_fhkst01010300_schema.json`

```json
{
  "provider": "KIS",
  "tr_id": "FHKST01010300",
  "description": "국내주식 시간별체결 (틱 데이터)",
  "collected_at": "2026-01-23T12:00:00+09:00",
  "request_params": {
    "symbol": "005930",
    "time": "150000"
  },
  "response": {
    "rt_cd": "0",
    "msg1": "정상처리 되었습니다.",
    "output": [
      {
        "stck_cntg_hour": "150000",
        "stck_prpr": "70500",
        "cntg_vol": "100",
        "acml_vol": "12345678"
      }
    ]
  },
  "schema_analysis": {
    "type": "object",
    "fields": {
      "rt_cd": {
        "type": "string",
        "example": "0"
      },
      "output": {
        "type": "array",
        "item_count": 30,
        "sample_item": {
          "type": "object",
          "fields": {
            "stck_cntg_hour": {"type": "string"},
            "stck_prpr": {"type": "string"},
            "cntg_vol": {"type": "string"}
          }
        }
      }
    }
  }
}
```

### 5.2 문서 파일 (Markdown)

**위치**: `docs/specs/api_reference/schemas/README.md`

**내용**:
- 수집된 스키마 파일 목록
- 각 TR ID별 상태 (✅ SUCCESS / ❌ FAILED)
- 파일 링크
- 사용법 가이드

---

## 6. 스키마 활용

### 6.1 KISClient 구현 시

```python
# kis_client.py

def _build_request_body(self, tr_id: str, params: Dict) -> Dict:
    """스키마 기반 파라미터 구성"""
    
    # FHKST01010300: 시간별체결
    if tr_id == "FHKST01010300":
        # Schema: docs/specs/api_reference/schemas/kis_fhkst01010300_schema.json
        return {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": params["symbol"],
            "FID_INPUT_HOUR_1": params.get("time", "153000")
        }
```

### 6.2 응답 파싱 시

```python
async def _handle_response(self, response, tr_id: str) -> Dict:
    """스키마 기반 응답 처리"""
    data = response.json()
    
    # FHKST01010300 스키마 참조
    if tr_id == "FHKST01010300":
        # Schema 확인: output은 array 타입
        return {
            "status": "success",
            "data": data.get("output", []),
            "message": data.get("msg1")
        }
```

### 6.3 테스트 작성 시

```python
# Fixture 생성 시 실제 스키마 참조
def test_kis_tick_response():
    # Schema: kis_fhkst01010300_schema.json
    fixture = {
        "rt_cd": "0",
        "msg1": "정상처리",
        "output": [
            {
                "stck_cntg_hour": "150000",
                "stck_prpr": "70500",
                "cntg_vol": "100"
            }
        ]
    }
```

---

## 7. 트러블슈팅

### 7.1 "RATE_LIMITED" 응답

**증상**: `⏳ RATE_LIMITED - Waiting 5 seconds...`

**원인**: Rate Limiter 초과 (KIS: 20 req/s, Kiwoom: 10 req/s)

**해결**:
1. 테스트가 자동으로 5초 대기 후 재시도
2. 여전히 실패 시 `redis-gatekeeper` 로그 확인
3. Rate Limit 설정 확인 (`Ground Truth Policy Section 8.1`)

### 7.2 "NO_CLIENT_KIS" 에러

**증상**: `❌ No client registered for provider: KIS`

**원인**: Gateway Worker가 Real API Mode로 실행 중이 아님

**해결**:
```bash
# Mock Mode 확인
docker logs gateway-worker-real | grep "Mock Mode"

# Real API Mode로 재시작
docker-compose down gateway-worker-real
ENABLE_MOCK=false docker-compose up -d gateway-worker-real
```

### 7.3 "토큰 만료" 에러

**증상**: `rt_cd = "EGW00201"` 또는 `return_code = "9999"`

**원인**: Access Token 만료

**해결**:
```bash
# TokenManager 로그 확인
docker logs gateway-worker-real | grep "Token"

# Worker 재시작 (자동 토큰 갱신)
docker-compose restart gateway-worker-real
```

---

## 8. CI/CD 통합 (선택)

### 8.1 주기적 스키마 검증

**목적**: API 스키마 변경 감지

**Cron 작업**:
```bash
# 매일 오전 10시 (장 중) 스키마 수집
0 10 * * 1-5 /path/to/run_schema_discovery.sh
```

**스크립트 예시**:
```bash
#!/bin/bash
# run_schema_discovery.sh

cd /path/to/stock_monitoring

# 스키마 수집
PYTHONPATH=. poetry run pytest tests/integration/test_api_schema_discovery.py::test_discover_all_schemas -v -s -m manual

# Git 변경 확인
git diff docs/specs/api_reference/schemas/

# 변경 사항이 있으면 알림
if [ $? -eq 0 ]; then
    echo "⚠️ API Schema changed! Review required."
    # Slack/Discord 알림 전송
fi
```

---

## 9. 관련 문서

- **KIS TR ID Reference**: `docs/specs/api_reference/kis_tr_id_reference.md`
- **Kiwoom TR ID Reference**: `docs/specs/api_reference/kiwoom_tr_id_reference.md`
- **Ground Truth Policy**: `docs/governance/ground_truth_policy.md`
- **API Hub v2 Overview**: `docs/specs/api_hub_v2_overview.md`
- **ISSUE-041**: `docs/issues/ISSUE-041.md`

---

## 10. 다음 단계

### 스키마 수집 후:

1. **스키마 리뷰**: 생성된 JSON 파일 검토
2. **KISClient 구현**: 수집된 스키마 기반 파라미터/응답 처리
3. **Unit Test 작성**: Fixture 기반 테스트 (실제 스키마 사용)
4. **문서화**: KIS/Kiwoom TR ID Reference 업데이트

---

**Document Owner**: Developer Persona  
**Last Updated**: 2026-01-23  
**Test Status**: Ready for Execution
