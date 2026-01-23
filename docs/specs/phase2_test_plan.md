# Phase 2 테스트 계획 문서

**Document ID**: ISSUE-037-E  
**Author**: QA Persona  
**Date**: 2026-01-23  
**Reviewer**: QA  

---

## 1. 원칙

**실제 API 호출 금지**: 모든 테스트는 Mock/Fixture 기반

---

## 2. 디렉토리 구조

```
tests/
├── unit/
│   ├── test_kis_client.py        (Fixture 기반)
│   ├── test_kiwoom_client.py     (Fixture 기반)
│   └── test_token_manager.py     (Redis Mock)
└── integration/
    └── test_real_api_call.py      (수동 실행, CI 제외)
```

---

## 3. CI 제외 방법

```python
# test_real_api_call.py

import pytest

@pytest.mark.manual  # CI에서 제외
@pytest.mark.asyncio
async def test_kis_real_call():
    """실제 KIS API 호출 (수동 실행 전용)"""
    client = KISClient()
    result = await client.execute("FHKST01010100", {"symbol": "005930"})
    assert result["status"] == "success"
```

**CI 실행**:
```bash
pytest -m "not manual"  # manual 태그 제외
```

---

## 4. Mock 기반 테스트 예시

```python
@pytest.mark.asyncio
async def test_kis_client_with_fixture():
    """Fixture 기반 테스트"""
    fixture = load_fixture("kis_candle_response.json")
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = httpx.Response(200, json=fixture)
        
        client = KISClient(...)
        result = await client.execute("FHKST01010100", {...})
        
        assert result["status"] == "success"
```

---

**Review Status**: ⏳ Pending (QA)  
**Implementation**: All tests must use Fixtures
