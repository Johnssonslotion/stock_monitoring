# Governance v2 Guide: "The Workflow Revolution"

이 문서는 프로젝트의 거버넌스 v2 체계와 10대 워크플로우 활용법을 정리한 공식 가이드입니다. 

---

## 1. 10대 거버넌스 워크플로우 (The Arsenal)

이제 다음 명령어들을 통해 프로젝트를 관리할 수 있습니다. 각 명령어는 슬래시 커맨드(`/[command]`) 형태로 호출하거나 자연어로 요청할 수 있습니다.

### 🏛️ Governance & Decisions
- **`/create-rfc`**: RFC 문서 자동 생성 (표준 템플릿 + 번호 채번)
- **`/create-spec`**: 기능/모듈 명세서 작성 (기존 코드 분석 포함)
- **`/run-gap-analysis`**: 코드-문서 불일치 정밀 진단
- **`/council-review`**: 6인 Council 공식 협의 (No Summary 원칙 강제)

### 📈 Project Management
- **`/create-roadmap`**: 로드맵 및 하위 문서 구조(Phase/Spec/Tasks) 자동 생성
- **`/brainstorm`**: 아이디어 기록 및 인큐베이팅 (Seed → Sprouting → Mature)
- **`/activate-deferred`**: 이연 작업(Deferred Work)을 활성화하여 백로그로 이동

### 💻 Git & Quality Operations
- **`/create-issue`**: 이슈 생성 및 전용 Feature/Fix 브랜치 자동 생성
- **`/hotfix`**: 긴급 장애 대응 (main 브랜치 직접 수정 및 백포트 자동화)
- **`/merge-to-develop`**: **품질 게이트** 자동 통과 후 병합 (Gap Analysis 자동 실행)

---

## 2. 개정된 헌법 (Constitution v2.5)

[.ai-rules.md](../../.ai-rules.md)는 이제 **워크플로우 기반 통치**를 명문화합니다.

> **Law #6 (Workflow First)**: AI는 모든 주요 작업을 시작하기 전 해당하는 워크플로우 슬래시 커멘드가 존재하는지 확인하고 이를 준수해야 한다. (No Spec, No Code)

---

## 3. 핵심 관리 도구 활용법

### 📋 [Deferred Work Registry](./deferred_work.md)
승인되었으나 우선순위에 밀려 미뤄진 작업들을 체계적으로 추적합니다. 잊혀지지 않도록 '트리거'를 설정하고, `/activate-deferred` 명령어로 활성화합니다.

### 💡 Idea Incubator (`docs/ideas/`)
아이디어가 로드맵에 안착하기 전까지 자유롭게 발전시키고 페르소나의 피드백을 받는 전용 공간입니다. `/brainstorm` 명령어로 시작하세요.

---

## 4. 품질 게이트 (Quality Gates)

모든 코드 병합은 `/merge-to-develop`을 통해 다음을 자동으로 검증합니다:
1. **Unit Tests**: `pytest` 통과 여부
2. **Gap Analysis**: 코드와 문서의 일관성 (P0 이슈 발생 시 병합 차단)
3. **Council Review**: 아키텍처 변경 시 6인 페르소나 협의 승인

---

## 5. 관련 문서
- [Constitution (Constitutional Index)](../../.ai-rules.md)
- [Governance History](./HISTORY.md)
- [Documentation Standard](./documentation_standard.md)
- [Workflows README](../../.agent/workflows/README.md)
