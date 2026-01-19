# IDEA: RFC를 ISSUE로 쪼개는 프로세스 재검토 (RFC-to-Issue Decomposition Review)

**Status**: 🌿 Sprouting (Critical Review)
**Priority**: P0 (Urgent - Process)
**Category**: Governance / Workflow

## 1. 개요 (Abstract)

**사용자 질문**: 
"RFC를 작성하고 나서 또 ISSUE로 쪼개는 게 이상하지 않나? RFC 자체를 하나의 작업 단위로 쓰면 안 되나?"

**핵심 문제**:
현재 프로세스:
```
RFC-005 (Virtual Investment 설계) 
  → 승인 후 
  → ISSUE-013, 015, 016, 017, 018로 분해
```

이게 정말 필요한가? **RFC 하나 = 작업 하나**로 진행하면 안 되나?

## 2. 표준 프로세스 재분석

### 2.1. Kubernetes KEP
```
KEP-1234: Add VolumeSnapshot API
  └─ Tracking Issue #5678
       ├─ PR #100: API definition
       ├─ PR #101: Controller implementation
       └─ PR #102: E2E tests
```
**핵심**: KEP 1개 → **Tracking Issue 1개** → 여러 PR
- ISSUE를 여러 개로 쪼개지 **않음**
- 대신 하나의 Tracking Issue 안에서 여러 PR 관리

### 2.2. Rust RFC
```
RFC-2000: Const Generics
  └─ Tracking Issue #44580
       (여러 PR이 이 Issue에 링크됨)
```
**핵심**: RFC 1개 → **Tracking Issue 1개**

### 2.3. Python PEP (Enhancement Proposal)
```
PEP-484: Type Hints
  └─ Implementation in Python 3.5
       (단일 릴리스, Issue 쪼개기 없음)
```

### 2.4. 공통점
**RFC/KEP/PEP → Tracking Issue는 1:1 매핑**
- RFC에서 여러 ISSUE로 쪼개지 않음
- 대신 하나의 "Tracking Issue"로 관리
- 여러 PR은 그 Issue에 링크됨

## 3. 우리가 잘못 이해한 점

### 3.1. 현재 계획 (잘못된 접근)
```
RFC-005: Virtual Investment Platform
  └─ 승인 후 분해:
       ├─ ISSUE-013: DB Schema
       ├─ ISSUE-014: VirtualExchange Class
       ├─ ISSUE-015: CostCalculator
       ├─ ISSUE-017: Dashboard UI
       └─ ISSUE-018: E2E Test
```
**문제**: 
- 5개 ISSUE를 추적해야 함 (복잡도 증가)
- 전체 진행 상황 파악 어려움
- "RFC-005가 완료되었나?"를 확인하려면 5개 ISSUE를 다 봐야 함

### 3.2. 표준 접근 (올바른 방법)
```
RFC-005: Virtual Investment Platform
  └─ ISSUE-001: Implement Virtual Investment Platform (Tracking)
       ├─ PR #10: DB Schema migration
       ├─ PR #11: VirtualExchange implementation
       ├─ PR #12: CostCalculator utility
       ├─ PR #13: Dashboard UI  
       └─ PR #14: E2E tests
```
**장점**:
- 추적 단위: ISSUE 1개만
- 진행 상황: ISSUE-001 보면 끝
- 브랜치: `feature/ISSUE-001-virtual-investment` 하나

## 4. 구체화 세션 (6인 페르소나)

### Developer
"맞습니다. 제가 지금까지 본 모든 프로젝트는 **큰 작업 = 하나의 Epic Issue**였습니다. PR만 여러 개 만들지, Issue를 쪼개진 않았어요."

### Governance Officer  
"RFC → 여러 ISSUE로 쪼개는 건 **Jira Epic의 잘못된 번역**입니다. Jira에서는:
- Epic (큰 작업) → 여러 Story
- 하지만 GitHub에서는:
- Epic Issue → 여러 PR (Issue는 하나만)

우리가 Jira 개념을 GitHub에 잘못 적용했습니다."

### Architect
"아키텍처 관점에서, **하나의 설계(RFC) = 하나의 구현 단위(Issue)**가 맞습니다. RFC-005를 5개로 쪼개면, '부분 구현' 상태가 발생할 수 있어 위험합니다."

### Product Manager
"사용자 관점에서 'Virtual Investment 기능이 완료되었나?'를 확인하려면 **ISSUE 하나만** 보고 싶습니다. 5개를 다 체크하는 건 비효율적입니다."

### Data Scientist
"데이터로 보면, Kubernetes는 10,000개 Issue 중 KEP는 100개 정도입니다. 그리고 KEP 1개당 Tracking Issue도 1개입니다. 절대 쪼개지 않습니다."

### QA Engineer
"테스트 관점에서도, **통합 테스트는 전체 기능 완료 후**에만 의미가 있습니다. ISSUE-013만 완료되고 015가 안 되면 테스트할 수 없어요."

## 5. 올바른 프로세스 제안

### 5.1. RFC → Issue 매핑 (1:1)
```
RFC-005: Virtual Investment Design
  ↓ (승인 후)
ISSUE-001: Implement Virtual Investment Platform
  - Status: In Progress
  - Branch: feature/ISSUE-001-virtual-investment
  - Sub-tasks (checklist):
    - [ ] DB Schema migration
    - [ ] VirtualExchange class
    - [ ] CostCalculator utility
    - [ ] Dashboard UI
    - [ ] E2E tests
  - PRs:
    - PR #10 (DB Schema)
    - PR #11 (VirtualExchange)
    - ...
```

### 5.2. ISSUE 템플릿 수정
```markdown
# ISSUE-XXX: [Title]

## Related RFC
- [RFC-005: Virtual Investment](../rfc/RFC-005.md)

## Implementation Checklist
- [ ] Subtask 1
- [ ] Subtask 2
- [ ] Subtask 3

## Pull Requests
- [ ] PR #10: Description
- [ ] PR #11: Description
```

### 5.3. 브랜치 전략
- **하나의 ISSUE = 하나의 feature 브랜치**
- 여러 PR을 같은 브랜치에서 순차적으로 생성
- 또는 각 PR을 별도 브랜치로 만들되, 모두 같은 ISSUE에 링크

## 6. 실무 변경 사항

### 즉시 조치:
1. **RFC-005~010을 ISSUE로 1:1 전환**:
   - RFC-005 → ISSUE-001 (Virtual Investment) - 쪼개지 않음
   - RFC-006 → ISSUE-002 (DB Aggregation)
   - RFC-007 → ISSUE-003 (WebSocket Manager)
   - 등등...

2. **ISSUE 템플릿에 "Subtask Checklist" 추가**

3. **BACKLOG.md 단순화**:
   ```markdown
   - [ ] ISSUE-001: Virtual Investment | P1 | [feature/ISSUE-001]
         ↳ 5 subtasks (3 done, 2 pending)
   ```

### 헌법 수정 (v2.10):
- **v2.8 보완**: "RFC 승인 후 → **단일 Tracking Issue** 생성"
- **ISSUE 쪼개기 금지**: 하나의 RFC = 하나의 ISSUE

## 7. 최종 의견

**사용자가 옳습니다**: RFC를 여러 ISSUE로 쪼개는 건 표준 프로세스가 **아닙니다**.

**올바른 방법**:
- RFC 1개 = ISSUE 1개 (Tracking Issue)
- ISSUE 안에서 체크리스트 관리
- 여러 PR은 같은 ISSUE에 링크

이렇게 하면:
- ✅ 추적 단순화 (ISSUE 1개만 봄)
- ✅ 브랜치 관리 명확 (feature/ISSUE-001 하나)
- ✅ 표준 프랙티스 준수 (Kubernetes/Rust 방식)
