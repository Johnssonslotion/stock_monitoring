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

### Step B: Spec Standardization
- `docs/specs/api_specification.md`가 로드맵의 "Pillar 0" 표준을 만족하는지 확인. (Dual Socket 관련 내용은 제거하거나 주석 처리)

## Verification
- 로드맵이 "Process Over Feature" 기조를 정확히 반영하고 있는가?
- Dual Socket 코드가 현재 실행(Active)되지 않도록 안전장치가 있는가? (Safe Default)
