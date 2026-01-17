# Issue 재정렬 계획 (Issue Reorganization Plan)

**일자**: 2026-01-17  
**목적**: Constitution v2.8 기준에 따라 RFC 필요 항목은 RFC로 전환하고, 나머지 ISSUE 번호를 재정렬

## 재정렬 매핑 (Renumbering Map)

### RFC로 전환 (6건)
| 기존 | 새 RFC | 제목 | 사유 |
|------|--------|------|------|
| ISSUE-001 | **RFC-005** | Virtual Investment Platform | DB Schema + Adapter Pattern + E2E |
| ISSUE-003 | **RFC-006** | DB View & Aggregation Restoration | TimescaleDB Schema 변경 |
| ISSUE-004 | **RFC-007** | WebSocket Connection Manager | 아키텍처 결정 + 통합 테스트 |
| ISSUE-008 | **RFC-008** | OrderBook Streaming | 복잡한 Delta 로직 |
| ISSUE-009 | **RFC-009** | Execution Streaming | Whale 감지 알고리즘 |
| ISSUE-012 | **RFC-010** | Correlation Engine | pandas 의존성 + NLP |

### ISSUE 유지 및 재정렬 (7건)
| 기존 | 새 번호 | 제목 | 상태 |
|------|---------|------|------|
| ISSUE-002 | **ISSUE-002** | Backlog ID 표준화 | ✅ 완료 (유지) |
| ISSUE-005 | **ISSUE-001** | Data Gap Detection & Filling | 단순 알고리즘 |
| ISSUE-006 | **ISSUE-003** | API Error Handling & Logging | 로깅 강화 |
| ISSUE-007 | **ISSUE-004** | Chart Zoom & Holiday | ✅ 완료 (유지) |
| ISSUE-010 | **ISSUE-005** | Candle Data Service | 단일 API 엔드포인트 |
| ISSUE-011 | **ISSUE-006** | Market Sector Service | 배치 작업 |
| ISSUE-013 | **ISSUE-007** | Whale Alert System | Webhook 연동 |

## 작업 순서

1. **RFC 문서 생성** (6건)
   - `docs/rfc/RFC-005-virtual-investment.md`
   - `docs/rfc/RFC-006-db-aggregation.md`
   - `docs/rfc/RFC-007-websocket-manager.md`
   - `docs/rfc/RFC-008-orderbook-streaming.md`
   - `docs/rfc/RFC-009-execution-streaming.md`
   - `docs/rfc/RFC-010-correlation-engine.md`

2. **기존 ISSUE 문서 이동** (RFC로 전환된 것들)
   - `docs/issues/ISSUE-001.md` → `docs/issues/legacy/ISSUE-001-virtual-investment.md`
   - 나머지도 동일하게 legacy로 이동

3. **ISSUE 재번호화**
   - `docs/issues/ISSUE-005.md` → `docs/issues/ISSUE-001.md` (내용 업데이트)
   - 나머지도 매핑에 따라 rename + 내용 수정

4. **BACKLOG.md 업데이트**
   - RFC 섹션 추가
   - ISSUE 번호 전부 새 번호로 변경
