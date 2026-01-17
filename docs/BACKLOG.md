# Project Backlog: Backend Integration & Data Pipeline

> **Governance Notice**: 
> 본 백로그의 작업은 **Live Market Data Collection**에 영향을 주지 않도록, 장 마감 후 또는 별도의 Staging 환경에서 진행해야 합니다.

## RFC (Request for Comments) - 설계 대기 중

복잡한 아키텍처 결정이 필요한 항목들입니다. RFC 승인 후 ISSUE로 분해됩니다.

- [ ] **RFC-005**: Virtual Investment Simulation Platform | P1
- [ ] **RFC-006**: DB View & Aggregation Restoration Strategy | P0
- [ ] **RFC-007**: WebSocket Connection Multiplexing Architecture | P1
- [ ] **RFC-008**: OrderBook Delta Streaming Design | P1
- [ ] **RFC-009**: Execution Streaming & Whale Detection | P1
- [ ] **RFC-010**: Correlation Engine & NLP Integration | P3

---

## Issues (Live) - 구현 작업

단순 구현 작업들입니다. 바로 시작 가능합니다.

- [ ] **ISSUE-001**: 데이터 누락 감지 및 채우기 로직 (Data Gap Detection) | P2
- [x] **ISSUE-002**: 백로그 이슈 ID 표준화 | P1 | ✅ 완료
- [ ] **ISSUE-003**: API 에러 핸들링 및 로깅 (API Error Handling & Logging) | P2
- [x] **ISSUE-004**: 차트 줌 오류 및 휴장일 처리 | P1 | ✅ 완료
- [ ] **ISSUE-005**: 캔들 데이터 서비스 (Candle Data Service) | P2
- [ ] **ISSUE-006**: 시장 섹터 서비스 (Market Sector Service) | P2
- [ ] **ISSUE-007**: 고래 알림 시스템 (Whale Alert System) | P3

---

## 참고: 재정렬 내역 (2026-01-17)

**RFC로 전환된 항목** (Constitution v2.8 기준):
- `ISSUE-001` (Virtual Investment) → `RFC-005`
- `ISSUE-003` (DB Aggregation) → `RFC-006`
- `ISSUE-004` (WebSocket Manager) → `RFC-007`
- `ISSUE-008` (OrderBook Streaming) → `RFC-008`
- `ISSUE-009` (Execution Streaming) → `RFC-009`
- `ISSUE-012` (Correlation Engine) → `RFC-010`

**번호 재정렬된 항목**:
- `ISSUE-005` → `ISSUE-001` (Data Gap Detection)
- `ISSUE-006` → `ISSUE-003` (API Error Handling)
- `ISSUE-007` → `ISSUE-004` (Chart Zoom - 완료)
- `ISSUE-010` → `ISSUE-005` (Candle Service)
- `ISSUE-011` → `ISSUE-006` (Market Sector)
- `ISSUE-013` → `ISSUE-007` (Whale Alert)

상세: `docs/governance/issue_reorganization_plan_2026-01-17.md`
