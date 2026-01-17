# Documentation Standard & Change Management Protocol (Atlassian Style)

## 1. 개요 (Overview)
본 문서는 프로젝트의 모든 지적 자산(문서, 코드, 의사결정)을 **'엔터프라이즈 레벨(Enterprise Level)'**로 관리하기 위한 표준을 정의한다.
Atlassian(Jira/Confluence)의 철학을 차용하여, 모든 변경 사항은 **추적 가능(Traceable)**하고 **합의(Agreed)**되어야 한다.

## 2. 문서화 헌장 (Documentation Charter)
1.  **Code is not Truth**: 코드는 '현재 상태'일 뿐, '의도'가 아니다. 의도는 반드시 문서(Spec/ADR)로 남겨야 한다.
2.  **Single Source of Truth (SSoT)**: 모든 정보는 오직 한 곳에만 존재해야 한다. 중복된 정보는 반드시 하나를 원본으로 지정하고 링크한다.
3.  **Living Document**: 업데이트되지 않는 문서는 '쓰레기'다. 문서는 코드와 동일한 생명주기(Lifecycle)를 가진다.

## 3. 변경 관리 프로세스 (Change Management via RFC)
주요 기능 추가, 아키텍처 변경 등 **Major Change** 발생 시, 코딩 전 **RFC(Request for Comments)** 과정을 필수적으로 거쳐야 한다.
- **Trigger**: DB 스키마 변경, 외부 API 연동, 핵심 로직 수정, 인프라 변경.
- **Workflow**:
    1.  `docs/rfc/YYYY-MM-DD-title.md` 작성.
    2.  6인 페르소나(Council) 검토 및 토론.
    3.  승인(Approved) 시 `implementation_plan.md`에 반영 후 코딩 시작.

### RFC 템플릿
```markdown
# RFC: [Title]
- **Status**: Proposed / Approved / Rejected
- **Author**: [Persona Name]
- **Date**: YYYY-MM-DD

## 1. 배경 (Context)
왜 이 변경이 필요한가? 현재의 문제점은 무엇인가?

## 2. 제안 내용 (Proposal)
구체적으로 무엇을 바꿀 것인가? (Technical Spec 포함)

## 3. 영향 분석 (Impact Analysis)
- **Data**: 기존 데이터 마이그레이션이 필요한가?
- **Cost**: 추가 비용이 발생하는가? (Zero Cost 원칙)
- **Risk**: 예상되는 부작용은?
```

## 4. 아키텍처 의사결정 기록 (ADR)
기술적인 선택(Technology Choice)이나 설계 원칙(Design Principle)을 결정했을 때 기록한다.
- **Location**: `docs/adrs/`
- **Format**: [MADR](https://adr.github.io/madr/) 스타일 준수.
- **예시**: "왜 RabbitMQ 대신 Redis Pub/Sub을 선택했는가?"

## 5. AI Enforcement (LLM 준수 수칙)
AI(LLM)는 다음 수칙을 알고리즘적으로 강제해야 한다.
1.  **Self-Constitution Check**: 사용자의 요청을 받으면, 즉시 코드를 수정하지 말고 **"관련된 Spec/RFC가 있는가?"**를 먼저 검색한다.
2.  **Veto Power**: 스펙이 없거나 RFC가 승인되지 않은 상태에서 코딩을 요청받으면, **"No Spec, No Code"** 원칙을 들어 거부(Veto)하고 문서 작성을 역제안한다.
3.  **Linkage**: 모든 커밋 메시지와 PR에는 `Ref: RFC-001`, `Spec: backend_spec.md`와 같은 참조 링크를 달아야 한다.

## 6. 문서 구조 표준 (Directory Standard)
```bash
docs/
├── governance/       # 규칙, 표준 (Constitution)
├── ideas/            # 아이디어 인큐베이터 (신규)
├── specs/            # 기능 명세 (Single Source of Truth)
├── rfc/              # 변경 제안 (Proposed Changes)
├── adrs/             # 의사결정 기록 (Decisions)
├── manuals/          # 사용자 가이드 (How-to)
└── testing/          # 테스트 전략 및 레지스트리
```

## 7. 워크플로우 활용 (Workflow Automation)
반복적인 거버넌스 프로세스는 `.agent/workflows/`에 정의된 워크플로우를 사용하여 일관성을 확보한다.

**주요 워크플로우:**
- `/create-rfc`: RFC 문서 생성 (템플릿 자동 적용)
- `/create-spec`: Spec 문서 작성 (코드 분석 포함)
- `/run-gap-analysis`: 코드-문서 불일치 탐지 (주기적 Audit)
- `/council-review`: 6인 Council 협의 진행
- `/activate-deferred`: 이연 작업 활성화
- `/create-roadmap`: 프로젝트 로드맵 및 구조 자동 생성

**참조**: [Workflows README](../../.agent/workflows/README.md)

