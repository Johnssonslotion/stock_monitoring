# IDEA: Timezone Aware Recovery & Strict KST Handling
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1

## 1. 개요 (Abstract)
데이터 복구 스크립트 작성 시 시스템 로컬 시간(UTC)과 한국 시장 시간(KST, UTC+9)의 혼동으로 인해 로직 오류(예: 루프 진입 실패)가 빈번하게 발생함. 이를 방지하기 위해 모든 날짜/시간 처리를 **KST Aware**하게 강제하는 표준 패턴 도입이 필요함.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: `datetime` 객체 생성 시 명시적으로 KST Timezone을 주입하거나, 프로젝트 전역 유틸리티(`Example: get_kst_now()`)를 사용하면 9시간 시차로 인한 데이터 누락이나 Future Timestamp 오류를 100% 방지할 수 있다.
- **기대 효과**:
    - 긴급 복구(Hotfix) 시 실수 방지.
    - 데이터 정합성 보장 (DB 저장 시각과 마켓 시간 일치).

## 3. 구체화 세션 (Elaboration)
- **Architect**: "Python `zoneinfo` 모듈을 표준으로 채택하고, 모든 `datetime.now()` 호출을 금지하는 Linter 규칙을 고려해야 함."
- **Developer**: "`scripts/recovery/` 하위 스크립트들은 `utils.time_utils`를 필수로 상속받도록 템플릿화하자."
- **QA**: "테스트 코드에서도 Mocking 시 KST 기준인지 UTC 기준인지 명확히 해야 함."

## 4. 로드맵 연동 시나리오
- **Pillar**: Reliability & Quality Assurance
- **Action Item**: `Development Guide`에 Timezone 처리 규칙 추가 및 `BaseRecovery` 클래스에 KST 유틸리티 내장.
