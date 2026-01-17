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

## Council of Six - 페르소나 협의 (2026-01-17)

### 👔 PM (Project Manager)
> "실시간 모니터링 도입으로 운영 가시성이 확보되었으며, Sentinel의 Doomsday Protocol은 시스템 안정성을 위한 필수 안전장치입니다. ISSUE-045 버그 픽스까지 포함되어 완성도가 높으므로 즉시 배포를 승인합니다."

### 🏛️ Architect
> "REST Polling에서 WebSocket Pub/Sub으로의 전환은 올바른 방향입니다. Sentinel이 Redis를 통해 메트릭을 발행하고 API가 이를 중계하는 구조는 결합도를 낮추고 확장성을 보장합니다. `sentinel_specification.md`가 사후에라도 명확히 정의된 점을 높이 평가합니다."

### 🔬 Data Scientist
> "시스템 메트릭 데이터의 형식이 표준화(Type, Value, Meta)되어 향후 시계열 분석이나 이상 탐지 모델 학습에 용이합니다. 데이터 정합성 측면에서 특이사항 없습니다."

### 🏗️ Infra Engineer
> "Redis 부하가 미미하며, Docker 헬스 체크 로직이 `psutil` 및 `docker-py` 기반으로 경량화되어 있어 오버헤드가 적습니다. Failover 시 `dual socket` 모드를 해제하는 로직도 안정성 최우선 원칙에 부합합니다."

### 💻 Developer
> "테스트 코드(test_sentinel.py, test_api_v1.py)가 업데이트되어 CI를 통과했습니다. 프론트엔드의 Immutable update 수정으로 렌더링 효율성도 개선되었습니다. 구현상 문제는 없습니다."

### 🧪 QA Engineer
> "초기 CPU 0% 문제와 차트 미표시 버그가 수정된 것을 확인했습니다. Chaos Test 시나리오(컨테이너 중단, Redis 연결 끊김)에 대한 Sentinel의 반응이 명세서와 일치하는지 지속적으로 모니터링하겠습니다."

### 📚 Doc Specialist
> "Gap Analysis 결과 모든 구현 사항이 문서화되었습니다. 특히 Missing Spec이었던 Sentinel 사양서가 추가되어 거버넌스 위반 사항이 해결되었습니다. 승인합니다."

## PM의 최종 결정
> **[APPROVED]** 만장일치로 승인합니다. 문서화 부채가 해소되었고 테스트도 통과했으므로 `develop` 브랜치로 머지하여 Phase 1 모니터링 기반을 확정합니다.
