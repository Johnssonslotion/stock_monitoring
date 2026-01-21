# ADR-005: Schema Triple-Lock Enforcement

## Status
✅ Approved (by Council of Six & User)

## Context
시스템 아카이버(`TimescaleArchiver`)의 자가 치유(`init_db`) 기능에 과도하게 의존하면서, 실제 DB 스키마와 마이그레이션 SQL, 그리고 Python 모델 간의 불일치(Schema Drift)가 발생함. 특히 중요한 타임스탬프 필드가 누락되어 데이터 품질 저하가 확인됨.

## Decision
모든 스키마 변경 시 다음 세 가지 요소를 동시에 검증하고 커밋해야 하는 **'Schema Triple-Lock'** 원칙을 도입한다.

1. **API Spec (OpenAPI/Swagger)**: 인터페이스 정의
2. **Python Model (Pydantic)**: 애플리케이션 내 데이터 구조
3. **DB Migration SQL**: 실제 저장소 스키마 정의

**세부 규칙**:
- 아카이버의 `init_db`는 연결 및 최소 구조 확인용으로만 사용하며, 스키마 정의의 SSoT는 마이그레이션 SQL로 제한한다.
- `from_ws_json` 등 수집 시점에서 시간을 고정하여 `received_time`의 일관성을 확보한다.

## Consequences
- 스키마 변경 시 작업 공수가 약간 늘어날 수 있으나, 데이터 정합성과 재현성이 완벽히 보장됨.
- `preflight_check.py` 등을 통한 자동화된 스키마 대조 테스트 구축 가능.

## Compliance
- `docs/governance/development.md`에 명문화
- `.agent/workflows/create-spec.md`, `council-review.md`에 검증 단계 추가
