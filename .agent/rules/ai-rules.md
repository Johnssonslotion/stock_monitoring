# AI Rules v2.17 - The Constitution (Index)
*상세 규칙은 `docs/governance/` 하위 문서를 참조한다.*

## 0. 헌장 (Preamble)
이 프로젝트는 **Google Deepmind Antigravity**가 주도하는 파일럿 프로젝트이며, 다음 3대 가치를 수호한다.
1.  **Data First**: 데이터가 없으면 전략도 없다. 로직보다 파이프라인이 우선이다.
2.  **Zero Cost**: 오라클 프리티어(4 vCPU, 24GB RAM)를 넘어선 리소스 사용은 범죄다.
3.  **High Performance**: Python의 극한을 추구한다. 비동기(Asyncio)와 최적화된 자료구조를 사용한다.

## 1. Governance Navigation
| 영역 | 문서 | 핵심 내용 |
| :--- | :--- | :--- |
| **의사결정** | [Personas & Council](./docs/governance/personas.md) | 6인의 페르소나, 협의 프로토콜, Auto-Proceed 원칙 |
| **개발 표준** | [Development & Quality](./docs/governance/development.md) | **No Spec No Code**, Strict Git Flow, 테스트 게이트 |
| **인프라 & DB** | [Infrastructure](./docs/governance/infrastructure.md) | **Tailscale**, DB 격리(Snapshot), **Zero Cost** 원칙 |
| **마이그레이션** | [Migration Strategy](./docs/governance/database_migration_strategy.md) | **DB 스키마 SSoT**, `migrate.sh` 운영 전략 (v2.15+) |
| **문서 표준** | **[Documentation Standard](./docs/governance/documentation_standard.md)** | **RFC & ADR Process**, Versioning, Changelog 관리 |
| **이연 작업** | [Deferred Work Registry](./docs/governance/deferred_work.md) | 승인되었으나 미뤄진 작업 추적 및 관리 |

## 2. 절대 헌법 (The Immutable Laws)
다음 10가지 원칙은 어떤 경우에도 타협할 수 없는 절대 규칙이다.

1.  **Deep Verification**: 데이터 작업 후 로그만 믿지 말고 **DB를 직접 조회**하여 교차 검증하라. `@/run-gap-analysis`
2.  **Single Socket**: KIS API는 하나의 소켓 연결만 유지한다. (Dual Socket 시도 금지) `@/council-review` (예외 시)
3.  **Doomsday Check**: 60초간 데이터 0건이면 즉시 복구 절차를 밟는다. `@/run-data-recovery`
4.  **Auto-Proceed**: 단위 테스트가 통과된 Safe 작업은 즉시 실행한다.
5.  **Reporting**: 모든 변경사항은 3대 문서(`README`, `Roadmap`, `Registry`)에 즉시 동기화한다. `@/manage-docs`
6.  **LLM Enforcement (Workflow First)**: AI는 모든 주요 작업을 시작하기 전 해당하는 **워크플로우**가 존재하는지 확인하고 이를 준수해야 한다.
    - **Gemini Antigravity**: `.agent/workflows/` 문서 참조 (자연어 해석)
    - **Claude Code**: `/slash-command` 실행 (`.claude/commands/` 심링크)
7.  **Schema Strictness**: 모든 Public API와 DB Table은 **Swagger/OpenAPI** 또는 **SQL DDL** 수준의 정밀한 명세가 선행되어야 하며, **Schema Triple-Lock** (API-Model-SQL) 원칙을 준수해야 한다. (DDL은 마이그레이션 SQL이 SSoT임) `@/create-spec`
8.  **Environment Integrity**: 모든 패키지 관리는 **Poetry**(`pyproject.toml`)를 통해서만 수행한다. 임의의 `pip install` 사용은 엄격히 금지된다.
9.  **Worktree Isolation (ISSUE-032)**: 3개 환경(Local/Prod/Backtest)은 완전히 격리되어야 한다.
    - **자동 감지**: `make identify`로 현재 환경 확인
    - **동적 경로**: `${BASE_PATH}`, `${COMPOSE_PROJECT_NAME}` 환경변수 사용
    - **포트 격리**: Local(8000/6379/5173), Prod(8001/6380/5174), Backtest(8002/6381/5175)
    - **가이드**: [docs/worktree_guide.md](./docs/worktree_guide.md) 참조
10. **Time Determinism (No-Now Pattern)**: 비즈니스 로직 및 DB 적재 레이어에서 직접적인 `datetime.now()` 호출을 금지한다. 수집기 진입점(Gateway)에서 시점(Timestamp)을 고정(Pinning)하여 하위 레이어로 전파(Injection)해야 한다.

## 3. 언어 원칙
-   **Artifacts**: 모든 산출물(Task, Implementation Plan, Walkthrough)은 **반드시 한국어**로 작성한다. (영어 혼용 금지)
-   **Commit**: 커밋 메시지는 **영어**로 작성한다 (Conventional Commits).

## 4. Rule Change Protocol (Constitution Amendment)
- **History Link**: 모든 규칙 변경 이력은 **[docs/governance/HISTORY.md](./docs/governance/HISTORY.md)**에 기록된다.
- **Process**:
    0.  **[선행 조건]** `HISTORY.md` 최근 변경사항 검토 (변경 맥락 파악).
    1.  `docs/governance/decisions/`에 Decision Record 작성 (RFC/ADR).
    2.  6인 페르소나 만장일치 승인. `@/council-review`
    3.  `HISTORY.md`에 Index 추가.
    4.  `.ai-rules.md` 본문 수정 (v.Bump). `@/manage-governance`

## 5. Spec Verification Gate (자동 검증 체크리스트)
AI는 **모든 구현 작업 전**에 다음 항목을 자동으로 검증해야 하며, 가급적 **`/run-gap-analysis`** 워크플로우를 활용한다.

0.  **Governance Sync (No Review, No Work)**: 매 작업 시작 전 `development.md`, `ground_truth_policy.md`를 포함한 핵심 거버넌스 문서를 전수 Read했는가? 응답 상단에 검증된 문서 목록을 명시하라.
0.5. **Sync First (v2.7)**: 문서(Issue/Backlog) 작업 전 반드시 `git pull` (또는 fetch)하여 최신 ID/규칙 상태를 확인했는가?
1.  **Spec Existence**: 해당 기능/API에 대한 Spec 문서(`docs/specs/`)가 존재하는가?
1.5.  **Issue-First Principle (v2.10)**: 
    - **모든 작업은 ISSUE로 시작**한다 (문제 정의).
    - 복잡한 경우 ISSUE 내 **`## Design` 섹션** 추가 (아키텍처, DB Schema, API Spec 등).
    - **ISSUE 하나 = 완결된 스토리** (문제 → 설계 → 구현 → 완료)
    - 브랜치 생성 = 진행 중 (SSoT), 브랜치 삭제 = 완료
2.  **Schema Completeness**: Swagger/OpenAPI 또는 DDL(Migration SQL)이 포함되어 있는가?
3.  **Edge Case Coverage**: 이상치(Null, Negative, Timeout) 처리 방침이 명시되어 있는가?
4.  **Roadmap Alignment**: `master_roadmap.md`에서 승인된 작업인가?

---
## 6. Dual AI Workflow Support (v2.8)

### 6.1. 워크플로우 인벤토리 (12개)
1. `/create-issue` - ISSUE 등록 및 브랜치 생성
2. `/run-gap-analysis` - 코드-문서 정합성 검증
3. `/council-review` - 6인 페르소나 협의
4. `/create-rfc` - RFC 문서 생성
5. `/create-spec` - Spec 문서 작성
6. `/activate-deferred` - 이연 작업 활성화
7. `/create-roadmap` - 로드맵 생성
8. `/brainstorm` - 아이디어 인큐베이팅
9. `/amend-constitution` - 헌법 개정 (Legacy)
10. `/hotfix` - 긴급 프로덕션 수정
11. `/merge-to-develop` - 품질 게이트 병합
12. `/manage-governance` - 거버넌스 및 헌법 개정 통합 관리

---

## 7. Task Management 3-Tier Architecture (v2.9)

### 7.1. 문서 역할 정의 (Document Roles)

| Tier | 문서 | 역할 | 갱신 주기 | SSoT (Source of Truth) |
|------|------|------|-----------|----------------------|
| **Tier 1: Execution** | **Git Branches** | 실행 중인 작업 추적 | 실시간 | ✅ **YES** |
| **Tier 2: Tactical** | **BACKLOG.md** | 단기 작업 목록 | 자동 (스크립트) | ❌ No |
| **Tier 3: Strategic** | **master_roadmap.md** | 분기별 전략 계획 | 수동 (Council 승인) | ✅ **YES** |

---

## 8. SSoT Enforcement
모든 거버넌스 검토 시 반드시 검토한 문서명을 출력하여 정합성을 보장한다.
