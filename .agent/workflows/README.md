# Workflows Directory

이 디렉토리에는 프로젝트의 표준화된 작업 프로세스(Workflows)가 정의되어 있습니다.

## 사용 방법

각 워크플로우는 `/[workflow-name]` 형태의 슬래시 커맨드로 호출할 수 있습니다.

**예시:**
```
/create-rfc
/activate-deferred
```

또는 자연어로 요청:
```
"새로운 RFC 만들어줘"
"Gap 분석 돌려줘"
```

---

## 거버넌스 워크플로우 (Governance)

### 1. `/create-rfc` - RFC 제정
- **목적**: 주요 변경사항에 대한 RFC 문서 생성
- **Trigger**: DB 스키마 변경, API 연동, 아키텍처 변경
- **Output**: `docs/governance/decisions/RFC-XXX_[title].md`

### 2. `/create-spec` - Spec 작성
- **목적**: 기능 또는 모듈의 명세서 작성
- **Trigger**: 신규 기능 개발, Gap Analysis에서 누락 발견
- **Output**: `docs/specs/[category]/[name].md`

### 3. `/run-gap-analysis` - Gap 분석
- **목적**: 코드와 문서 간 불일치 탐지
- **Trigger**: 분기별 검토, 릴리스 전, 리팩토링 후
- **Output**: `docs/gap_analysis_report_[date].md`

### 4. `/council-review` - Council 협의
- **목적**: 6인 페르소나의 공식 협의 진행
- **Trigger**: 아키텍처 변경, 규칙 위반, 프로덕션 장애
- **Output**: `implementation_plan.md` (Council 섹션)

### 5. `/activate-deferred` - 이연 작업 활성화
- **목적**: Deferred Work를 BACKLOG로 이동
- **Trigger**: 사용자가 작업 시작 결정
- **Output**: `BACKLOG.md` 업데이트, `task.md` 생성

---

## 프로젝트 관리 워크플로우 (Project Management)

### 6. `/create-roadmap` - 로드맵 생성
- **목적**: 프로젝트 로드맵 및 하위 구조 자동 생성
- **Trigger**: 신규 프로젝트, 분기별 계획, 대규모 리팩토링
- **Output**: 
  - `docs/strategies/[project]_roadmap.md`
  - `docs/ideas/[project]/` (아이디어 뱅크)
  - `docs/phases/[project]/phase_X/tasks.md`

### 7. `/brainstorm` - 아이디어 인큐베이팅
- **목적**: 모호한 아이디어를 기록하고 로드맵/RFC로 발전
- **Trigger**: 아이디어 발생, 시스템 개선 제안
- **Output**: `docs/ideas/[project]/ID-[title].md` 생성 및 로드맵 예비 항목 등록

---

## Git 작업 워크플로우 (Git Operations)

### 7. `/create-issue` - 이슈 생성 및 트래킹
- **목적**: 버그/기능 요청 이슈 생성 및 브랜치 자동 생성
- **Trigger**: 버그 발견, 기능 요청, 사용자 명령
- **Output**: 
  - ISSUE-[NUMBER] 생성
  - Feature/Fix 브랜치 생성
  - BACKLOG.md 업데이트

### 8. `/hotfix` - 긴급 프로덕션 수정
- **목적**: 프로덕션 긴급 이슈 신속 대응
- **Trigger**: 프로덕션 장애, 보안 취약점, Critical Bug
- **Output**:
  - `main` 브랜치에서 hotfix 브랜치 생성
  - 최소 수정 → 배포
  - `develop` 백포트

### 9. `/merge-to-develop` - Develop 브랜치 병합
- **목적**: 품질 게이트를 거친 자동 병합
- **Trigger**: Feature 완료, PR 생성
- **Output**:
  - Gap Analysis 자동 실행
  - 조건부 Council Review
  - 병합 + 태그 생성

---

## 워크플로우 생성 가이드

새로운 워크플로우 추가 시 다음 구조를 따르세요:

```markdown
---
description: [Short description for LLM]
---

# Workflow: [Name]

## Trigger Conditions
- [Condition 1]
- [Condition 2]

## Steps
1. **[Step Name]**
   - Details
   - Sub-steps

## Example Usage
**User says:**
- "[Command 1]"
- "[Natural language request]"

**AI will:**
1. [Action 1]
2. [Action 2]
```

---

## 관련 문서
- [Governance Personas](../docs/governance/personas.md)
- [Documentation Standard](../docs/governance/documentation_standard.md)
- [Deferred Work Registry](../docs/governance/deferred_work.md)
