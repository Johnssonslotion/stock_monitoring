# Implementation Plan - Process Formalization First

## Goal Description
1.  **Prioritize Process**: 기능 구현(Dual Socket)은 **백로그(Backlog)**로 연기(Defer)하고, **거버넌스와 문서화 프로세스 정립**에 집중합니다.
2.  **Formalize Current State**: 현재 혼재된 규칙과 문서 체계를 명확한 **프로세스(Constitution -> History -> Spec -> Roadmap)**로 정리합니다.

# [ISSUE-044] Backend Monitoring & Observability Upgrade

본 계획은 `/api/system/metrics`를 WebSocket 기반 실시간 스트리밍으로 전환하여 모니터링 대시보드의 실시간성을 확보하는 것을 목표로 합니다.

## User Review Required

> [!IMPORTANT]
> **Architecture Change**: REST API 폴링 방식에서 Redis Pub/Sub을 연동한 WebSocket 기반 전송 방식으로 변경됩니다. 이는 아키텍처 변경(Architecture Change)에 해당하므로 Council Review가 필수입니다.

---

## Proposed Changes

### [Backend] Monitoring API & Sentinel
- **[MODIFY] [system.py](file:///home/ubuntu/workspace/stock_backtest/src/api/routes/system.py)**: `/ws/system` 엔드포인트 추가 및 Redis Pub/Sub 리스너 구현.
- **[MODIFY] [sentinel.py](file:///home/ubuntu/workspace/stock_backtest/src/monitoring/sentinel.py)**: 데이터 수집 후 Redis `system:metrics` 채널로 메시지 Publish 로직 추가.

### [Frontend] System Dashboard
- **[MODIFY] [SystemDashboard.tsx](file:///home/ubuntu/workspace/stock_backtest/src/web/src/components/SystemDashboard.tsx)**: Polling(`setInterval`) 제거, `StreamManager`를 통한 WebSocket 연동 및 `system_metric` 이벤트 핸들링 추가.
- **[MODIFY] [StreamManager.ts](file:///home/ubuntu/workspace/stock_backtest/src/web/src/StreamManager.ts)**: 시스템 모니터링용 전용 채널(`system`) 처리 로직 보강.

---

## Verification Plan

### Automated Tests
- **Unit Tests**:
  - `python3 -m pytest tests/test_system_ws.py` (신규 파일 생성 예정)
  - WebSocket 핸드셰이크 및 인증 검증.
- **Gap Analysis**:
  - `/run-gap-analysis` 실행하여 `realtime_metrics_ws.md` 명세 충족 여부 확인.

### Manual Verification
- `SystemDashboard`가 5초 폴링 없이도 리소스 변화를 즉시 시각화하는지 UI에서 확인.
- 컨테이너 중단 시 대시보드 아이콘이 즉각적으로 붉은색으로 변하는지 확인.
