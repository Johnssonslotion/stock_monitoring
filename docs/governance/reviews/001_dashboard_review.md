# 🧐 Council of Six Review: Dashboard & Safety Latch

**Date**: 2026-01-14
**Topic**: System Dashboard Implementation & Environment Separation Enforcement

## 1. 👔 Project Manager (Focus: Value & Risk)
> "환경 분리(Safety Latch)는 훌륭한 '비용 절감' 조치입니다. 운영 중 실수로 인한 다운타임 비용을 예방하니까요. 다만, **E2E 검증이 수동(`curl`)에 의존하는 건 확장성 측면에서 0점**입니다. 기능이 추가될 때마다 매번 수동으로 칠 건가요?"
> **Verdict**: **Conditional Approval** (Must automate verification).

## 2. 🏛️ Solution Architect (Focus: Pattern & Scale)
> "`SystemDashboard.tsx`가 API에 직접 의존하고 있습니다. Frontend와 Backend 간의 **스키마 계약(Schema Contract)**이 느슨합니다. API 응답의 `meta` 필드가 JSON string으로 오는데, 이것이 클라이언트에서 파싱 실패하면 대시보드 전체가 깨질 수 있습니다."
> **Verdict**: **Request Refactor** (Add Schema Validation).

## 3. 🔬 Data Scientist (Focus: Data Integrity)
> "시스템 메트릭도 데이터입니다. `system_metrics` 테이블에 쌓이는 데이터가 시계열 분석에 적합한지 확인했나요? 현재 구조는 단순 조회용이라 분석용으로는 부족합니다만, 이번 스프린트 목표는 '모니터링'이니 넘어갑니다."
> **Verdict**: **Pass** (Scope limited to Ops).

## 4. 🔧 Infrastructure Engineer (Focus: Stability)
> "`Makefile`의 `preflight_check.sh`는 로컬 개발환경에서는 좋지만, **CI/CD 파이프라인에서는 독**이 될 수 있습니다. CI 서버는 `git status`가 항상 clean하지 않을 수 하거나 대화형(interactive) 입력이 불가능합니다. `NON_INTERACTIVE=1` 같은 우회로가 필요합니다."
> **Verdict**: **Changes Required** (Add CI bypass mode).

## 5. 🧪 QA Engineer (Focus: Coverage & Reliability)
> "**`curl` 한번 날려보고 E2E라고 부르는 건 모욕적입니다.** 진정한 E2E는 '원인(Sentinel)'부터 '결과(Dashboard UI)'까지의 데이터 **일치성**을 검증해야 합니다. Sentinel이 CPU 6.8%라고 보냈는데, UI에 6.8%라고 뜨나요? 이걸 검증하는 코드가 없으면 테스트가 아닙니다."
> **Verdict**: **REJECT** (Implement proper integration test).

## 6. 📝 Documentation Specialist (Focus: Clarity)
> "`preflight_check.sh`가 생겼다는 사실이 `README.md`나 `CONTRIBUTING.md`에 없으면 신규 개발자는 영문도 모른 채 배포에 실패할 것입니다."
> **Verdict**: **Pass** (But update docs).

---

## 🚀 Action Items
1.  **[QA]** `tests/e2e/test_system_dashboard.py` 작성: Sentinel -> API -> Response 검증 자동화.
2.  **[Infra]** `preflight_check.sh`에 `FORCE_DEPLOY` 플래그 추가.
3.  **[Arch]** API 응답 스키마(Pydantic) 강화 검토 (Backlog).
