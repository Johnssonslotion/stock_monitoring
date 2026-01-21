# IDEA: Issue-First 워크플로우 (Definitive Development Process)

**Status**: 🌳 Mature (Ready for Constitution)
**Priority**: P0 (Critical - Replaces v2.8)
**Category**: Governance / Workflow

## 1. 개요 (Abstract)

**사용자가 정의한 올바른 프로세스**:
```
1. ISSUE 발행 (문제 정의) ← 최우선 싱크
2. 복잡도 검토
   ├─ 단순 → 바로 브랜치 생성
   └─ 복잡 → RFC 작성 (설계 문서)
3. 브랜치 생성 (작업 시작)
   - 브랜치 존재 = "진행 중" (실시간 SSoT)
4. 구현 (여러 PR)
5. Merge & 브랜치 삭제
   - 브랜치 없음 = "완료"
```

**핵심 원칙**:
- **ISSUE = 살아있는 문서** (문제 → 설계 → 구현 → 완료)
- **RFC = ISSUE 내부의 설계 섹션** (필요시만)
- **Git Branch = 실행 상태의 SSoT**

## 2. 가설 및 기대 효과 (Hypothesis & Impact)

**가설**:
- ISSUE를 중심으로 모든 것을 관리하면, 추적이 단순해지고 표준 프랙티스를 준수할 수 있다.
- Git 브랜치를 실시간 상태 지표로 사용하면, 문서 수동 업데이트 불필요.

**기대 효과**:
1. **추적 단순화**: ISSUE 하나만 보면 전체 진행 상황 파악
2. **표준 준수**: Kubernetes, Rust, Linux 등 모든 주요 오픈소스 프로젝트 방식
3. **자동화**: 브랜치 기반 상태 → `sync-issue-status.sh`로 자동 동기화

## 3. 구체화 세션 (Elaboration - 6인 페르소나)

### Developer
"완벽합니다. 제가 일하던 모든 회사에서 이렇게 했습니다:
- GitHub Issue 생성
- 복잡하면 Issue 안에 'Design' 섹션 추가 (별도 RFC 문서 아님)
- `feature/ISSUE-123` 브랜치 생성
- 여러 PR을 같은 Issue에 링크
- 완료되면 브랜치 삭제

RFC를 별도로 관리하는 건 대기업(Google, Microsoft) 정도만 합니다."

### Governance Officer
"**Tracking 단위의 일원화**가 핵심입니다:
- ❌ RFC + ISSUE 2개 추적
- ✅ ISSUE 1개만 추적

ISSUE 템플릿에 '## Design (Optional)' 섹션을 추가하면, 간단한 것은 비우고 복잡한 것만 채우면 됩니다."

### Architect
"아키텍처 관점에서 **ISSUE = 변경 단위**입니다. 하나의 문제는 하나의 해결책으로 완결되어야 합니다. RFC-005를 5개 ISSUE로 쪼개는 건 '부분 구현' 리스크를 만듭니다."

### Product Manager
"로드맵 관점에서:
- Q1 Goal: Virtual Investment 기능
- Deliverable: ISSUE-001 (완료 or 진행 중)

RFC-005 + ISSUE-013~018이라고 하면, PM이 '뭘 봐야 하나?'라고 헷갈립니다."

### Data Scientist
"데이터로 검증:
- **Kubernetes**: 10,000 Issues, 100 KEPs (1%)
- **Rust**: 5,000 Issues, 50 RFCs (1%)
- **우리 (v2.8)**: 13 Issues, 6 RFCs (46%) ← **비정상**

1% 미만이 정상입니다."

### QA Engineer
"테스트 실행 시점:
- ISSUE 단위로 E2E 테스트 실행
- RFC가 '부분 승인'되면 테스트 불가능

ISSUE 하나 = 테스트 가능한 완결 단위여야 합니다."

## 4. 상세 프로세스 정의 (Detailed Workflow)

### 4.1. ISSUE 발행 (Phase 1: Problem Definition)
```bash
/create-issue
```
**입력**:
- Title: "Virtual Investment 기능 필요"
- Type: Feature
- Priority: P1

**출력**:
- `docs/issues/ISSUE-001.md` 생성
- BACKLOG.md 자동 추가
- **상태**: [ ] Open

### 4.2. 복잡도 검토 (Phase 2: Complexity Assessment)

**AI 자동 판단** (Constitution v2.8 기준):
- 3개 이상 파일 수정?
- DB Schema 변경?
- 새 외부 의존성?
- 아키텍처 패턴?
- E2E 테스트 필요?

**결과**:
- ✅ YES → "Design 섹션 필요" (RFC-like)
- ❌ NO → 바로 구현 가능

### 4.3. (복잡한 경우) Design 작성
```markdown
# ISSUE-001: Virtual Investment Platform

## Problem
백테스팅이 비현실적 (세금/수수료 미반영)

## Design (Architecture Decision)
- **Pattern**: Adapter Pattern
- **Components**: VirtualBroker, CostCalculator, Dashboard
- **DB Schema**: 
  - virtual_accounts
  - virtual_positions
  - virtual_orders
- **Integration**: StreamManager 연동

## Implementation Plan
- [ ] DB Migration
- [ ] VirtualBroker class
- [ ] CostCalculator utility
- [ ] Dashboard UI
- [ ] E2E tests

## Acceptance Criteria
- [ ] 세금 계산 정확도 99%+
- [ ] 슬리피지 시뮬레이션
```

### 4.4. 브랜치 생성 (Phase 3: Execution Start)
```bash
git checkout -b feature/ISSUE-001-virtual-investment
```
**효과**:
- `sync-issue-status.sh` 자동 감지
- BACKLOG.md: `- [/] ISSUE-001` (In Progress)

### 4.5. 구현 (Phase 4: Development)
```bash
# PR #10: DB Schema
git commit -m "feat(ISSUE-001): add virtual_accounts schema"

# PR #11: VirtualBroker
git commit -m "feat(ISSUE-001): implement VirtualBroker adapter"

# PR #12: CostCalculator
...
```

**모든 PR은 같은 ISSUE-001에 링크**

### 4.6. 완료 (Phase 5: Completion)
```bash
git checkout develop
git merge feature/ISSUE-001-virtual-investment
git branch -d feature/ISSUE-001-virtual-investment
git push origin :feature/ISSUE-001-virtual-investment  # 원격 삭제
```

**효과**:
- 브랜치 없음 → `sync-issue-status.sh` 자동 감지
- BACKLOG.md: `- [x] ISSUE-001` (Done)

## 5. 문서 구조 (Document Structure)

### 5.1. ISSUE 템플릿 (개선)
```markdown
# ISSUE-XXX: [Title]

**Status**: Open / In Progress / Done
**Priority**: P0-P3
**Type**: Bug / Feature / Epic

## Problem Description
[문제 정의]

## Design (Optional - 복잡한 경우만)
[아키텍처 설계, DB Schema, API Spec 등]

## Implementation Checklist
- [ ] Subtask 1
- [ ] Subtask 2

## Related PRs
- [ ] PR #10: Description
- [ ] PR #11: Description

## Acceptance Criteria
- [ ] 기능 X 동작
- [ ] 성능 Y 이상
```

### 5.2. RFC 사용 (극히 제한)
**RFC는 오직**:
- 프로젝트 전체 영향 (예: DB 교체 PostgreSQL → MongoDB)
- 하위 호환 깨는 변경 (예: API v1 → v2)
- **빈도: 연간 0~2개**

**RFC 예시** (진짜 RFC 수준):
- RFC-001: Monolith → Microservices 전환
- RFC-002: Python → Rust 마이그레이션

**NOT RFC** (일반 Epic Issue):
- Virtual Investment (큰 기능이지만 내부 구현)
- WebSocket Manager (아키텍처이지만 범위 한정)

## 6. 헌법 개정 제안 (Constitution v2.10)

### 6.1. v2.8 철회 내용
❌ 삭제:
> "RFC vs ISSUE Separation: 3개 이상 파일 수정 → RFC 필요"

### 6.2. v2.10 신규 조항
✅ 추가:
> **Issue-First Principle**:
> 1. 모든 작업은 ISSUE로 시작
> 2. 복잡도 검토 → Design 섹션 필요 여부 결정
> 3. 브랜치 생성 = 진행 중 (SSoT)
> 4. 브랜치 삭제 = 완료
> 5. RFC는 연간 1~2개 (프로젝트 전체 영향만)

## 7. 실무 적용 계획

### 즉시 조치:
1. **RFC-005~010 삭제**
2. **기존 ISSUE 재구성**:
   - ISSUE-001: Data Gap Detection (기존 유지)
   - ISSUE-002: Backlog 표준화 (완료)
   - ISSUE-003: API Error Handling
   - ISSUE-004: Chart Zoom (완료)
   - ISSUE-005: Virtual Investment (RFC-005 흡수)
   - ISSUE-006: DB Aggregation (RFC-006 흡수)
   - ISSUE-007: WebSocket Manager (RFC-007 흡수)

3. **ISSUE 템플릿 업데이트**: Design 섹션 추가

4. **워크플로우 수정**: `/create-issue`에 Design 필요 여부 체크

## 8. 최종 의견

**결론**: ISSUE-First 프로세스는 **표준 프랙티스**이며, v2.8의 "RFC 남발"은 오류였습니다.

**다음 단계**:
1. Constitution v2.10 개정
2. RFC-005~010 정리 (ISSUE로 통합)
3. `/create-issue` 워크플로우 업데이트
