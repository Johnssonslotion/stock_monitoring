# IDEA: RFC vs ISSUE 재고 (Reconsidering RFC vs ISSUE Separation)

**Status**: 🌿 Sprouting (Critical Review)
**Priority**: P0 (Urgent - Governance)
**Category**: Governance / Process

## 1. 개요 (Abstract)

**사용자 지적**: "ISSUE와 구현전략을 동시에 하는 게 이상한데? ISSUE는 ISSUE고, RFC를 굳이 나눠야 할 필요성이 있나?"

**핵심 문제**: 
방금 Constitution v2.8에서 도입한 "RFC vs ISSUE 분리"가 실제 개발 프로세스에서 **불필요한 복잡도**를 증가시킬 수 있습니다.

## 2. 표준 개발 프로세스 비교 (Industry Standard Review)

### 2.1. GitHub/GitLab Standard Practice
```
Issue = 작업 단위 (설계 + 구현 모두 포함)
  ├─ Discussion (설계 논의)
  ├─ Implementation (코드 작성)
  └─ Review & Merge
```
**특징**: RFC 개념 없음. 모든 설계는 ISSUE 내 Discussion 섹션으로 충분.

### 2.2. Kubernetes KEP (Kubernetes Enhancement Proposal)
```
KEP (RFC급) = 아키텍처 레벨 변경 (예: 새 API 그룹 추가)
  └─ Tracking Issue = KEP 구현을 위한 작업 목록
Issue = 버그 수정, 단순 개선
```
**특징**: KEP는 **연간 1~2개 수준**의 대형 변경에만 사용.

### 2.3. Rust RFC Process
```
RFC = 언어 스펙 변경 (예: 새 키워드 추가)
Issue = 라이브러리 개선, 버그 수정
```
**특징**: RFC는 **하위 호환성을 깨는 변경**에만 사용.

### 2.4. Linux Kernel
```
Mailing List = 모든 논의 (설계 포함)
Patch = 구현
```
**특징**: RFC 개념 자체가 없음.

## 3. 현재 우리 프로젝트 문제점

### 3.1. RFC-005~010 실제 분석
| RFC | 내용 | RFC 필요? | 실제 적합 분류 |
|-----|------|-----------|---------------|
| RFC-005 | Virtual Investment | ❓ Maybe | **Epic ISSUE** (큰 작업, 하지만 RFC는 과함) |
| RFC-006 | DB Aggregation | ❌ **NO** | **ISSUE** (TimescaleDB 설정일 뿐) |
| RFC-007 | WebSocket Manager | ❓ Maybe | **Epic ISSUE** (아키텍처이지만 범위 한정) |
| RFC-008 | OrderBook Streaming | ❌ **NO** | **ISSUE** (새 API 추가일 뿐) |
| RFC-009 | Execution Streaming | ❌ **NO** | **ISSUE** (RFC-008과 유사) |
| RFC-010 | Correlation Engine | ❓ Maybe | **Research Task** (PoC 필요) |

**결론**: 6개 중 **0~2개만** 진짜 RFC 수준. 나머지는 "큰 ISSUE"일 뿐.

### 3.2. 불필요한 오버헤드
- **문서 2벌**: RFC 문서 + 나중에 ISSUE로 다시 분해
- **의사결정 지연**: RFC 승인 대기 → 구현 지연
- **혼란**: "이게 RFC인가 ISSUE인가?" 계속 고민

## 4. 구체화 세션 (Elaboration - 6인 페르소나)

### Developer
"솔직히 말하면, 저는 ISSUE 하나에 `## Design` 섹션 추가하는 게 훨씬 편합니다. RFC 따로 쓰고, 승인받고, 다시 ISSUE로 쪼개는 건 너무 번거롭습니다."

### Governance Officer
"**역할 재정의**가 필요합니다:
- **RFC**: **연간 1~2개 수준**의 대형 아키텍처 변경 (예: Python → Rust 전환, Monolith → MSA)
- **Epic Issue**: 여러 PR이 필요한 큰 작업 (예: Virtual Investment)
- **Issue**: 단일 PR로 끝나는 작업

RFC를 너무 낮은 기준으로 남발하면 안 됩니다."

### Architect
"제 경험상, RFC는 **여러 팀이 영향받는 변경**에만 필요합니다. 우리는 1인 팀이므로, Epic Issue로 충분합니다."

### Product Manager
"사용자 관점에서는 **ISSUE 하나만 추적**하고 싶습니다. RFC-005 → ISSUE-014~018로 쪼개지면, 전체 진행 상황을 파악하기 어렵습니다."

### Data Scientist
"통계적으로, Kubernetes도 **전체 Issue의 1% 미만**이 KEP(RFC)입니다. 우리가 50% (6/13)를 RFC로 분류한 건 과도합니다."

### QA Engineer
"테스트 관점에서, RFC든 ISSUE든 **동일한 테스트 전략**이 필요합니다. 문서 형식만 다를 뿐, 검증 절차는 같습니다."

## 5. 제안하는 개선안 (Proposed Solution)

### 5.1. 새로운 분류 체계

```
ISSUE (모든 작업의 기본 단위)
  ├─ Type: Bug / Feature / Epic / Research
  ├─ Priority: P0~P3
  ├─ Complexity: Simple / Medium / Complex
  └─ Template:
       - Problem
       - **Design (복잡한 경우만)**
       - Implementation Plan
       - Acceptance Criteria
```

**RFC는 폐기하고, 대신**:
```
Epic Issue = 복잡한 작업
  - 여러 Sub-Issue로 분해 가능
  - `## Design` 섹션 필수
  - Council 승인 필요 (복잡도에 따라)
```

### 5.2. RFC 사용 기준 (극도로 제한)

RFC는 **오직** 다음 경우에만:
1. **하위 호환성을 깨는 변경** (예: API v1 → v2 마이그레이션)
2. **프로젝트 전체 영향** (예: 데이터베이스 교체)
3. **외부 공개 문서** (예: 오픈소스 프로젝트의 큰 변경)

**예상 빈도**: 연간 0~2개

### 5.3. 실무 예시

| 작업 | 기존 분류 | 새 분류 | 이유 |
|------|-----------|---------|------|
| Virtual Investment | RFC-005 | **Epic ISSUE-001** | 큰 작업이지만, 내부 구현일 뿐 |
| DB Aggregation | RFC-006 | **ISSUE-002** (Complex) | 설정 변경, RFC 불필요 |
| OrderBook Streaming | RFC-008 | **ISSUE-003** (Epic) | 새 기능, 하지만 API 추가일 뿐 |

## 6. Action Items (v2.8 롤백 제안)

### 즉시 조치:
1. **RFC-005~010 삭제**
2. **ISSUE-001 (Data Gap)을 ISSUE-008로 변경**
3. **기존 RFC를 Epic ISSUE로 전환**:
   - RFC-005 → ISSUE-001 (Virtual Investment) - Epic
   - RFC-006 → ISSUE-002 (DB Aggregation) - Complex
   - RFC-007 → ISSUE-003 (WebSocket Manager) - Epic
   - 나머지는 Medium/Simple로 재분류

### 헌법 수정 (v2.10):
- **v2.8 일부 철회**: "RFC vs ISSUE Separation" 조항 삭제
- **대체**: "Issue Complexity Classification" (Simple/Medium/Complex/Epic)
- **RFC 기준 상향**: 연간 1~2개 수준의 대형 변경만

## 7. 참고 (References)

- GitHub Issue Templates Best Practice
- Kubernetes KEP Process (very selective RFC usage)
- JIRA Epic vs Story vs Task hierarchy

## 8. 최종 의견

**결론**: RFC와 ISSUE를 분리한 v2.8은 **과도한 프로세스**였습니다. 
**권장**: Epic Issue 개념으로 통합하고, RFC는 극히 제한적으로만 사용.
