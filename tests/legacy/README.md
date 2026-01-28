# Legacy Tests

**Deprecated Date**: 2026-01-28
**Reason**: ISSUE-044 아키텍처 리팩토링

이 폴더의 테스트는 레거시 모듈에 대한 것으로, 일반 테스트 실행에서 제외됩니다.

## 포함된 테스트

| 테스트 파일 | 대상 모듈 | 상태 |
|------------|----------|------|
| `test_recovery_logic.py` | `BackfillManager` | Deprecated |

## 실행 방법 (필요 시)

```bash
# 레거시 테스트만 실행
pytest tests/legacy/ -v

# 레거시 테스트 제외하고 실행 (기본)
pytest tests/ --ignore=tests/legacy/
```

## 관련 문서
- [ISSUE-044](../../docs/issues/ISSUE-044.md)
- [Legacy Modules](../../src/data_ingestion/recovery/legacy/README.md)
