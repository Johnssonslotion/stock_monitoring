# ADR-008: Integration of Migration SSoT into Constitution

## Status
✅ Proposed (Strict Workflow Enrollment)

## Context
프로젝트에 실존하는 마이그레이션 시스템(`migrate.sh`)과 전략 문서가 헌법 네비게이션 테이블에서 누락되어 AI의 인식 사각지대가 발생함. 이로 인해 거버넌스 우회(하드코딩)와 데이터 적재 장애가 초래됨.

## Decision
마이그레이션 시스템을 헌법(`.ai-rules.md`)의 핵심 인프라 규정으로 공식 바인딩하고, 'Triple-Lock' 원칙을 기존 DoD #4의 하위 상세 지침으로 통합한다.

1. **Constitutional Binding**: `.ai-rules.md`의 `Governance Navigation`에 `database_migration_strategy.md`를 즉시 추가.
2. **Workflow Enforcement**: 모든 스키마 변경은 `/manage-governance`를 통해 `migrate.sh` 실행 여부를 반드시 검토함.
3. **System Restoration**: 고립되었던 `migrations/` 시스템을 유일한 스키마 SSoT로 재선언함.

## Consequences
- 지식의 고립(Isolation)으로 인한 AI의 '규칙 발명' 휴먼 에러를 방지함.
- 마이그레이션 시스템이 AI의 주류 탐색 경로에 배치되어 정목표 달성률이 향상됨.
- 배포 전 `migrate.sh status` 확인이 강제됨.
