---
description: Manage governance documents and ai-rules amendments with strict protocol
---

# Workflow: Manage Governance

이 워크플로우는 프로젝트의 거버넌스 문서(`docs/governance/`) 및 최고 법인 **헌법(.ai-rules.md)**을 수정하는 엄격한 절차를 관리합니다.

## Trigger Conditions
- 새로운 거버넌스 규칙 도입 필요 시
- 기존 규칙의 수정 또는 폐기 시
- 헌법(`ai-rules.md`) 개정 필요 시
- 사용자 명령: `/manage-governance`

## Steps

### 1. Context Analysis (맥락 파악)
- **Action**: `docs/governance/HISTORY.md`를 검토하여 최근 변경 사항 및 개정 맥락을 파악합니다.
- **Goal**: 중복되거나 상충되는 규칙이 없는지 확인합니다.

### 2. Decision Recording (의사결정 기록)
- **Action**: `docs/governance/decisions/`에 `ADR` (Architecture Decision Record) 또는 `RFC`를 작성합니다.
- **Rule**: 모호한 자연어 대신 정밀한 명세를 포함해야 합니다.

### 3. Consensus Building (합의 및 검토)
- **Action**: `/council-review` 워크플로우를 호출하여 6인 페르소나의 의견을 수렴합니다.
- **Goal**: PM의 최종 결정을 이끌어냅니다.

### 4. Logging Ledger (이력 기록)
- **Action**: `docs/governance/HISTORY.md`에 새로운 개정 이력을 추가합니다.
- **Format**: 버전 번호(vX.X) 및 상세 변경 내역을 포함한 Table 형식을 준수합니다.

### 5. Document Inception (문서 반영)
- **Action**: 타겟 문서(예: `.ai-rules.md`, `development.md`)의 본문을 수정합니다.
- **Version Bump**: 헌법 수정 시에는 반드시 버전 번호를 업데이트합니다.

### 6. Verification & Sync (검증 및 동기화)
- **Action**: `docs/README.md` 및 `master_roadmap.md` 등 연관된 문서 허브들을 최신화합니다.
- **Validation**: `/run-gap-analysis`를 실행하여 정합성을 최종 검증합니다.

### 7. Notify User
- 변경된 문서들의 링크와 `HISTORY.md`의 새로운 항목을 요약 보고합니다.

## Example Usage

**User says:**
- "/manage-governance"
- "스키마 검증 규칙을 거버넌스에 추가해줘"

**AI will:**
1. 관련 ADR 작성
2. Council Review 진행
3. HISTORY.md 기록
4. ai-rules.md 또는 관련 문서 수정
5. 최종 보고

## Integration
- Links to: `/council-review`, `/run-gap-analysis`
- Updates: `docs/governance/`, `.ai-rules.md`, `HISTORY.md`
