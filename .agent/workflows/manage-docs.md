---
description: 프로젝트 문서의 생애주기(생성, 통합, 정합성 검증, 아카이빙)를 관리합니다.
---
# Workflow: Manage Documentation

이 워크플로우는 문서의 파편화를 방지하고 **단일 진실 공급원(SSoT)**을 유지하기 위한 문서 관리 프로세스를 정의합니다.

## Trigger Conditions
- 새로운 기능 구현 시작 전 (Spec 작성)
- Gap Analysis 결과 발견된 불치사항 조치 시
- 분기별 문서 정수 조사 및 정리 세션
- 사용자 명령: `/manage-docs`

## Steps

### 1. Verification (정합성 검증)
**Action**: 현재 문서와 코드의 불일치 여부를 확인합니다.
- `/run-gap-analysis` 워크플로우를 호출하여 보고서를 생성합니다.
- 깨진 링크, 중복된 내용, 구버전 명세서를 식별합니다.

### 2. Normalization (표준화)
**Action**: 문서의 형식을 [Documentation Standard](file:///Users/bbagsang-u/workspace/stock_monitoring/docs/governance/documentation_standard.md)에 맞게 정규화합니다.
- 파일 경로는 상대 경로 대신 `file:///` 프로토콜을 포함한 절대 경로를 권장합니다.
- 이슈 번호 및 일자 형식을 준수합니다.

### 3. Consolidation & Hub Update (통합 및 인덱싱)
**Action**: 파편화된 정보를 통합하고 [Documentation Hub](file:///Users/bbagsang-u/workspace/stock_monitoring/docs/README.md)에 반영합니다.
- 유사한 주제의 짧은 문서들은 하나의 상세 문서로 통합합니다.
- 새로 생성된 문서는 `docs/README.md`의 적절한 섹션에 링크를 추가합니다.

### 4. Archiving (아카이빙)
**Action**: 더 이상 유효하지 않거나 기록용으로만 남겨야 할 문서를 격리합니다.
- 대상 문서를 `docs/ARCHIVE/` 디렉토리로 이동시킵니다.
- `docs/HISTORY.md`에 주요 변경 이력 및 통폐합 사실을 기록합니다.
- **자동 갱신**: 아카이빙 후 `docs/README.md` 인덱스에서 해당 링크를 제거하거나 `Archive` 섹션으로 이동시킵니다.

### 5. Final Audit
**Action**: PM 및 Doc Specialist 페르소나가 최종 정합성을 검토합니다.
- 모든 링크가 정상 작동하는지 확인합니다.
- `BACKLOG.md`와 개별 이슈 파일 간의 상태가 일치하는지 확인합니다.

## Promotion Rules
- **Draft** → **Official**: 6인 페르소나 협의 후 승인되었을 때.
- **Official** → **Archived**: 상위 버전이 배포되거나 기술 스택이 완전히 변경되었을 때.

## Integration
- Links to: `/run-gap-analysis`, `/create-spec`
- Updates: `docs/README.md`, `README.md`
