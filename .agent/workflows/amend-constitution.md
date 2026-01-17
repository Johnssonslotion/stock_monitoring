---
description: Amend the Constitution (.ai-rules.md) with strict governance tracking
---

# Workflow: Amend Constitution

이 워크플로우는 프로젝트의 최고 법인 **헌법(.ai-rules.md)**을 수정하는 엄격한 절차를 자동화합니다. 헌법 수정은 반드시 기록되어야 하며, 합의 과정을 거쳐야 합니다.

## Trigger Conditions
- `/brainstorm`을 통해 도출된 정책이 'Mature' 단계에 도달했을 때
- 긴급한 거버넌스 수정 필요 시 (`/hotfix` 레벨의 정책 변경)
- 사용자 명령: `/amend-constitution`

## Steps

### 1. Pre-requisite Check (선행 조건 확인)
**Action**: 변경하려는 내용이 RFC나 Decision Log로 존재하는지 확인
- **Input**: `RFC Document Path` (e.g., `docs/ideas/...` or `docs/rfc/...`)
- **Validation**: 해당 문서가 'Approved' 상태이거나 사용자가 명시적으로 승인했는지 확인.

### 2. Update History Ledger
**Action**: `docs/governance/HISTORY.md`에 변경 이력 기록
- **Format**:
  ```markdown
  ## [YYYY-MM-DD] Amendment v[Version]
  - **Subject**: [Title of Amendment]
  - **Reason**: [Why this change is needed]
  - **Reference**: [Link to RFC/Idea Doc]
  - **Author**: [Persona/User]
  ```

### 3. Amend Constitution
**Action**: `.ai-rules.md` 파일 수정
- **Version Bump**: 헤더의 버전 업데이트 (e.g., v2.5 -> v2.6)
- **Content Update**: 실제 규칙 조항 추가/수정/삭제.

### 4. Commit & Notify
**Action**: 변경사항 커밋 및 사용자 통지
- **Commit Message**: `chore(governance): amend constitution v[Version] - [Subject]`
- **Notification**:
  ```
  🏛️ Constitution Amended (v2.6)
  
  Subject: 문서 작업 전 동기화 강제
  Changes:
  1. Updated .ai-rules.md (Added 'Pre-condition' to Section 5)
  2. Logged in HISTORY.md
  
  The new rule is now in effect.
  ```

## Example Usage

**User says:**
- "/amend-constitution"
- "이 아이디어 헌법에 반영해줘"

**AI will:**
1. RFC/Idea 문서 확인
2. History 기록
3. ai-rules.md 수정
4. 보고

## Integration
- Updates: `.ai-rules.md`, `docs/governance/HISTORY.md`
