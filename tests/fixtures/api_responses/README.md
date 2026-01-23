# API Response Fixtures

외부 REST API 응답 샘플을 저장하여 스키마 호환성 테스트에 사용합니다.

## 파일 목록

| 파일명 | 설명 | 갱신 주기 |
|--------|------|----------|
| `kis_candle_response.json` | KIS 분봉 API 응답 샘플 | 주 1회 |
| `kis_tick_response.json` | KIS 틱 API 응답 샘플 | 주 1회 |
| `kiwoom_candle_response.json` | Kiwoom 분봉 API 응답 샘플 | 주 1회 |

## 샘플 갱신 방법

```bash
# 수동 갱신 (API 키 필요)
PYTHONPATH=. poetry run python scripts/update_api_fixtures.py

# CI 자동 갱신 (향후 구현)
# - 주 1회 스케줄 실행
# - 스키마 변경 시 PR 자동 생성
```

## 테스트 사용법

```python
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures/api_responses"

def load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)

# 테스트에서 사용
def test_kis_response_schema():
    data = load_fixture("kis_candle_response.json")
    model = CandleModel.model_validate(data)
    assert model.source_type == "REST_API_KIS"
```

## 관련 테스트

- `HUB-SCH-01`: KIS API 응답 스키마 검증
- `HUB-SCH-02`: Kiwoom API 응답 스키마 검증
- `HUB-SCH-03`: 스키마 변경 감지 (실제 API 호출)
