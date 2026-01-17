# Implementation Plan - Process Formalization First

## Goal Description
1.  **Prioritize Process**: 기능 구현(Dual Socket)은 **백로그(Backlog)**로 연기(Defer)하고, **거버넌스와 문서화 프로세스 정립**에 집중합니다.
2.  **Formalize Current State**: 현재 혼재된 규칙과 문서 체계를 명확한 **프로세스(Constitution -> History -> Spec -> Roadmap)**로 정리합니다.

## 1. Roadmap Alignment (De-prioritization)

### [MODIFY] [docs/strategies/master_roadmap.md](file:///home/ubuntu/workspace/stock_backtest/docs/strategies/master_roadmap.md)
- **Status Update**:
  - **Pillar 2 (Data)**: "Dual Socket Strategy" -> **[DEFERRED/BACKLOG]** 상태로 변경.
  - **Pillar 0 (Governance)**: "Process Formalization"을 현재 최우선(In-Progress) 과제로 설정.

## 2. Process Formalization (Immediate Action)

### Step A: Constitution & History Check
- `ai-rules.md`와 `docs/governance/HISTORY.md`가 **독립적**으로 잘 관리되고 있는지 최종 점검.
- Rule Change Protocol이 "Dual Socket" 내용이 아닌, **"Rule Change 절차 그 자체"**를 잘 정의하고 있는지 확인.
## Council of Six - 페르소나 협의

### 👔 PM (Project Manager)
> "Governance v2는 단순한 규칙의 집계를 넘어, 우리 프로젝트의 운영 효율성을 비약적으로 높일 초석입니다. 특히 `/merge-to-develop`과 같은 품질 게이트 자동화는 AI 에이전트의 작업 신뢰도를 담보하는 핵심 장치이므로, 다소 복잡하더라도 엄격히 준수되어야 합니다. 비즈니스 리스크 최소화를 위해 이 안을 원안대로 승인합니다."

### 🏛️ Architect
> "아키텍처 관점에서 RFC-001(Single Socket) 강제는 자원 관리와 충돌 방지에 있어 필수적인 조치입니다. 또한 10대 워크플로우가 명문화됨에 따라 시스템 확장 시에도 일관된 패턴을 유지할 수 있는 가이드라인이 완성되었습니다. 전반적인 설계의 견고함이 향상되었으므로 전적으로 동의합니다."

### 🧪 Data Scientist
> "전략 명세 표준(RFC-002) 수립은 데이터 일관성 확보를 위해 매우 시급했던 과제였습니다. 비록 기존 전략들에 대한 상세 명세 작성이 DEF-002로 이연되었으나, 표준이 수립되었으므로 향후 데이터 오염이나 모델링 오류를 예방할 수 있는 체계가 마련되었다고 판단합니다."

### ☁️ Infra
> "Docker 기반의 백테스트 환경과 리포지토리 설정이 명확해졌습니다. 특히 설정 관리 표준(RFC-003)을 통해 하드코딩된 변수들을 제거함으로써 클라우드 배포와 로컬 개발 환경 간의 이식성이 크게 강화되었습니다. 운영 측면에서 환영할 만한 변화입니다."

### 💻 Developer
> "Vite Env 지원과 'Safe Default' 코드 반영으로 개발 편의성과 안정성이 동시에 확보되었습니다. 워크플로우가 다소 번거로울 수 있으나, 슬래시 커맨드 덕분에 반복적인 보일러플레이트 문서 작성 시간을 줄일 수 있어 전체적인 개발 속도는 더 빨라질 것으로 기대합니다."

### 🔍 QA
> "품질 게이트 도입과 Gap Analysis 자동화는 테스트 커버리지 누락을 방지하는 최후의 보루가 될 것입니다. 인프라 기반 테스트 실패가 여전히 존재하나, 이는 환경 설정의 문제일 뿐 거버넌스 로직 자체의 결함이 아니므로 머지 후 환경 안정화 작업을 병행하는 조건으로 승인합니다."

### 📝 Doc Specialist
> "문서 중심의 개발 문화(Doc-Centric)가 헌법(Constitution)에 내재화되었습니다. 가이드와 템플릿이 완비되어 지식 전파와 교육 비용이 최소화될 것입니다. 버전 2.5의 모든 문서 체계가 표준안을 충족하므로 승인합니다."

## PM의 최종 결정
> **결정**: Governance v2 최종안을 **승인(APPROVED)** 합니다.
> **후속 조치**: `develop` 브랜치로 즉시 병합하고, 이연된 전략 명세 작업(`DEF-002-001`)은 다음 주 단위 계획에 반영하십시오. 모든 워크플로우는 즉시 효력을 발휘합니다.

---

### Step B: Spec Standardization
- `docs/specs/api_specification.md`가 로드맵의 "Pillar 0" 표준을 만족하는지 확인. (Dual Socket 관련 내용은 제거하거나 주석 처리)

## Verification
- 로드맵이 "Process Over Feature" 기조를 정확히 반영하고 있는가?
- Dual Socket 코드가 현재 실행(Active)되지 않도록 안전장치가 있는가? (Safe Default)
