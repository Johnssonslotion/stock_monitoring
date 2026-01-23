# API Response Fixtures

**Purpose**: TDD 지원 및 Ground Truth 검증을 위한 실제 API 응답 샘플 저장소

**Owner**: Data Scientist Persona  
**Last Updated**: 2026-01-23

---

## 1. 개요 (Overview)

이 디렉토리는 KIS 및 Kiwoom API의 실제 응답 샘플을 저장합니다.

### 목적
1. **TDD 지원**: 실제 API 호출 없이 응답 파싱 로직 테스트
2. **Data Transformation 검증**: API 응답 → CandleModel 변환 정확성 확인
3. **Ground Truth 보증**: source_type 필드가 올바르게 태깅되는지 검증
4. **스키마 변경 감지**: API 스키마 변경 시 조기 경고

---

## 2. 파일 목록

### KIS (한국투자증권)

| 파일명 | TR ID | 설명 | 갱신 날짜 |
|--------|-------|------|-----------|
| `kis_candle_response.json` | FHKST01010100 | 국내주식 분봉 조회 | 2026-01-23 |

**필드 매핑**:
- `stck_bsop_date`: 날짜 (YYYYMMDD)
- `stck_cntg_hour`: 시간 (HHMMSS)
- `stck_prpr`: 현재가
- `stck_oprc`: 시가
- `stck_hgpr`: 고가
- `stck_lwpr`: 저가
- `cntg_vol`: 거래량

### Kiwoom (키움증권)

| 파일명 | TR ID | 설명 | 갱신 날짜 |
|--------|-------|------|-----------|
| `kiwoom_candle_response.json` | opt10081 | 주식 분봉 조회 | 2026-01-23 |

**필드 매핑**:
- `종목코드`: 종목 코드
- `체결시간`: 시간 (HHMMSS)
- `현재가`: 현재가
- `시가`: 시가
- `고가`: 고가
- `저가`: 저가
- `거래량`: 거래량

---

## 3. Fixture 갱신 방법

### 수동 갱신 (개발 환경)

```bash
# API 키 설정
export KIS_APP_KEY="your_key"
export KIS_APP_SECRET="your_secret"
export KIWOOM_API_KEY="your_key"

# Fixture 수집 스크립트 실행
PYTHONPATH=. poetry run python scripts/update_api_fixtures.py
```

### 민감정보 제거 (Sanitization)

**반드시 제거**:
- 계좌번호
- 실명
- 전화번호
- API Key/Secret

**유지**:
- 종목 코드
- 가격 데이터
- 거래량
- 타임스탬프

---

## 4. 테스트 사용법

```python
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures/api_responses"

def load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)

# 테스트에서 사용
@pytest.mark.asyncio
async def test_kis_response_parsing():
    data = load_fixture("kis_candle_response.json")
    
    # Mock 응답 생성
    mock_response = httpx.Response(status_code=200, json=data)
    
    # 응답 처리
    client = KISClient(app_key="test", app_secret="test", access_token="test")
    result = await client._handle_response(mock_response, "FHKST01010100")
    
    assert result["status"] == "success"
    assert result["provider"] == "KIS"
```

---

## 5. Ground Truth 변환 규칙

| Provider | TR ID | source_type | 비고 |
|----------|-------|-------------|------|
| KIS | FHKST01010100 | `kis_rest` | 국내주식 분봉 |
| Kiwoom | opt10081 | `kiwoom_rest` | 주식 분봉 |

---

## 6. 관련 테스트

- `HUB-SCH-01`: KIS API 응답 스키마 검증
- `HUB-SCH-02`: Kiwoom API 응답 스키마 검증
- `HUB-SCH-03`: 스키마 변경 감지 (실제 API 호출)

**Test Files**:
- `tests/unit/test_kis_client.py`
- `tests/unit/test_kiwoom_client.py`
- `tests/integration/test_api_hub_schema.py`

---

**Owner**: Data Scientist  
**Review Cadence**: 분기 1회  
**Last Review**: 2026-01-23
