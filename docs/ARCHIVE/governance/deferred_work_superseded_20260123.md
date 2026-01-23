# Deferred Work Registry (이연 작업 등록부)

이연된 작업(Deferred Work)을 추적하고 관리하는 레지스트리입니다. RFC 승인은 되었으나 실제 구현이 미뤄진 작업, 또는 로드맵에는 있지만 우선순위가 낮아 대기 중인 작업을 기록합니다.

---

## 등록 원칙
1. **RFC 링크 필수**: 모든 이연 작업은 관련 RFC/ADR 문서를 참조해야 합니다.
2. **Trigger 명시**: 언제 작업을 시작할지 명확한 트리거 조건을 정의합니다.
3. **Auto-Expire**: 6개월 이상 방치된 작업은 자동으로 "Cancelled" 처리되거나 재검토됩니다.

---

## 1. Config 관리 고도화 (P1 - High Priority)

| 항목 | 내용 |
| :--- | :--- |
| **ID** | `DEF-003-001` |
| **Title** | 전략 파라미터 Config 분리 (RFC-003 Compliance) |
| **Related RFC** | [RFC-003](decisions/RFC-003_config_management_standard.md) |
| **Status** | ⏳ DEFERRED |
| **Assigned** | Developer + Architect |
| **Priority** | P1 (High) |
| **Trigger** | 사용자 일정 여유 확보 시 |
| **Dependencies** | - |
| **Scope** | - `configs/strategy_config.yaml` 표준 포맷 정의<br>- `src/core/config.py`에 `StrategyConfig` Pydantic 모델 추가<br>- `SampleMomentumStrategy` 등 전략 클래스 리팩토링 |
| **Implementation Plan** | [Link](/home/ubuntu/.gemini/antigravity/brain/d20082fe-6e04-4ba8-8324-cc86e25a09db/implementation_plan.md) |
| **Roadmap** | [Pillar 5: System Refactoring](../strategy/master_roadmap.md#pillar-5) |
| **Created** | 2026-01-17 |
| **Last Review** | 2026-01-17 |

---

## 2. 데이터 관리 및 최적화

| 항목 | 내용 |
| :--- | :--- |
| **ID** | `DEF-034-001` |
| **Title** | 틱 데이터 공백 복구 (Log + REST Hybrid) |
| **Related RFC** | [RFC-008](rfc/RFC-008-tick-completeness-qa.md) |
| **Status** | ⏳ DEFERRED |
| **Trigger** | 시스템 안정화 후 일괄 복구 필요 시 |
| **Priority** | P1 (High) |

| 항목 | 내용 |
| :--- | :--- |
| **ID** | `DEF-034-002` |
| **Title** | TimescaleDBPost-Market 최적화 자동화 |
| **Related RFC** | [ISSUE-034](../issues/ISSUE-034.md) |
| **Status** | ⏳ DEFERRED |
| **Trigger** | 장 마감 후 자동 스케줄링 (Cron) 적용 시 |
| **Priority** | P2 (Medium) |

---

## 3. 아키텍처 개선 및 리팩토링

| 항목 | 내용 |
| :--- | :--- |
| **ID** | `DEF-API-HUB-001` |
| **Title** | Unified API Hub v2 (Centralized REST Worker & Queue) |
| **Related RFC** | [Spec: API Hub](file:///home/ubuntu/workspace/stock_monitoring/docs/specs/api_hub_specification.md) |
| **Status** | ⏳ DEFERRED |
| **Trigger** | 2026-01-23 장 마감 후 또는 다음 스프린트 시작 시 |
| **Priority** | P1 (High) |
| **Scope** | - Redis 기반 리퀘스트 큐(`api:request:queue`) 구축<br>- REST API 전담 워커(`rest_worker.py`) 구현<br>- KIS/Kiwoom 호출부 통합 및 리팩토링 |
| **Created** | 2026-01-23 |

---

## 관리 프로세스
- **주기적 리뷰**: 매 분기 말 PM 페르소나가 검토.
- **활성화 (Activation)**: 사용자가 다음과 같이 명령 시 즉시 Todo로 이동.
  - 예: `"DEF-003-001 백로그로 활성화해줘"`
  - 예: `"Config 분리 작업 시작할게, activate"`
  - AI는 자동으로 `BACKLOG.md`에 추가하고 `task.md`를 생성함.
- **Status Update**: 트리거 조건 충족 시 → Status를 `🔄 ACTIVE`로 변경.
- **Archiving**: 완료 시 → "Done" 섹션으로 이동하고 완료일 기록.

