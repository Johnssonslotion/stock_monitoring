# ISSUE 전체 감사: RFC 필요 여부 분류

**감사 일자**: 2026-01-17  
**목적**: 현재 등록된 ISSUE-001 ~ ISSUE-013을 RFC 기준에 따라 재분류

## Decision Criteria (결정 기준)

다음 조건 중 **하나라도** 해당하면 **RFC 필요**:
- ✅ 3개 이상 파일/컴포넌트 수정
- ✅ DB Schema 변경
- ✅ 새로운 외부 의존성
- ✅ 아키텍처 패턴 결정 필요
- ✅ 통합/E2E 테스트 필요

---

## 분류 결과

| ID | 제목 | RFC 필요? | 이유 | 권장 조치 |
|----|------|-----------|------|-----------|
| **ISSUE-001** | Virtual Investment Platform | ⚠️ **YES** | • DB Schema 변경 (virtual_accounts, orders, positions)<br>• Adapter Pattern 설계 필요<br>• 4개 이상 컴포넌트 (VirtualExchange, CostCalculator, StreamManager, Dashboard)<br>• E2E 테스트 필요 | **RFC-005로 전환**<br>승인 후 ISSUE-014~018로 분해 |
| **ISSUE-002** | Backlog ID 표준화 | ✅ **NO** | • 문서 작업만 (코드 변경 없음)<br>• 단순 거버넌스 정리 | 유지 (완료됨) |
| **ISSUE-003** | DB View 재생성 | ⚠️ **YES** | • TimescaleDB Schema 변경<br>• Continuous Aggregates 정책<br>• 데이터 무결성 검증 필요 | **RFC-006으로 전환**<br>(단, 단순 복구라면 ISSUE 유지 가능) |
| **ISSUE-004** | WebSocket Manager | ⚠️ **YES** | • 아키텍처 결정 (Multiplexing 전략)<br>• Redis Pub/Sub 연동<br>• 3개 이상 컴포넌트 (Manager, Collector, Dashboard)<br>• 통합 테스트 필요 | **RFC-007로 전환** |
| **ISSUE-005** | Data Gap Detection | ✅ **NO** | • 단일 파일 (`candles.py`) 수정<br>• 알고리즘 구현만<br>• Unit Test로 검증 가능 | 유지 (ISSUE 적합) |
| **ISSUE-006** | API Error Handling | ✅ **NO** | • 단순 로깅 강화<br>• 에러 코드 정의<br>• 2개 파일 이하 | 유지 (ISSUE 적합) |
| **ISSUE-007** | Chart Zoom & Holiday | ✅ **NO** | • Frontend만 수정<br>• 단순 버그 수정<br>• E2E 테스트 (이미 완료) | 유지 (완료됨) |
| **ISSUE-008** | OrderBook Streaming | ⚠️ **MAYBE** | • 새 WebSocket 핸들러<br>• Delta 전송 로직<br>• 단일 컴포넌트 but 복잡한 로직 | RFC 권장<br>(또는 Spike로 PoC 후 결정) |
| **ISSUE-009** | Execution Streaming | ⚠️ **MAYBE** | • ISSUE-008과 유사<br>• Whale 감지 로직 (복잡도 중간) | RFC 권장 |
| **ISSUE-010** | Candle Data Service | ✅ **NO** | • 단일 API 엔드포인트<br>• CRUD 로직<br>• ISSUE-005와 연동 | 유지 (ISSUE 적합) |
| **ISSUE-011** | Market Sector Service | ⚠️ **MAYBE** | • 배치 작업 추가<br>• 섹터 집계 알고리즘<br>• 2개 컴포넌트 (Batch, API) | 복잡도에 따라<br>간단하면 ISSUE, 복잡하면 RFC |
| **ISSUE-012** | Correlation Engine | ⚠️ **YES** | • 외부 의존성 (pandas/numpy)<br>• NLP 뉴스 분석 (새 컴포넌트)<br>• 알고리즘 설계 필요 | **RFC-008로 전환** |
| **ISSUE-013** | Whale Alert System | ✅ **NO** | • 단순 Webhook 연동<br>• 기존 Execution Streaming에 Alert 추가<br>• 2개 파일 이하 | 유지 (단, ISSUE-009 의존성) |

---

## 요약 (Summary)

### ⚠️ RFC 필요 (6건 → 즉시 전환)
1. **ISSUE-001** → RFC-005: Virtual Investment Design
2. **ISSUE-003** → RFC-006: DB Aggregation Strategy (선택적)
3. **ISSUE-004** → RFC-007: WebSocket Multiplexing Architecture
4. **ISSUE-008** → RFC-008: OrderBook Delta Streaming (권장)
5. **ISSUE-009** → RFC-009: Execution Streaming & Whale Detection (권장)
6. **ISSUE-012** → RFC-010: Correlation Engine Design

### ✅ ISSUE 유지 (7건 → 바로 구현 가능)
- ISSUE-002 (완료)
- ISSUE-005: Data Gap Detection
- ISSUE-006: API Error Handling
- ISSUE-007 (완료)
- ISSUE-010: Candle Data Service
- ISSUE-011: Market Sector Service (복잡도 낮으면)
- ISSUE-013: Whale Alert (ISSUE-009 의존)

---

## 권장 조치 순서

1. **즉시**:
   - `ISSUE-001` → `RFC-005` 전환 및 작성 시작
   - `ISSUE-004` → `RFC-007` 전환 (이미 아키텍처 영향도 높음)
   
2. **단기** (1주 이내):
   - `ISSUE-012` → RFC-010 작성
   - `ISSUE-008, 009` → Spike PoC로 복잡도 검증 후 RFC 여부 최종 결정
   
3. **헌법 개정** (Constitution v2.8):
   - `.ai-rules.md` Section 5에 "RFC vs ISSUE Decision Tree" 추가
   - `/create-issue` 워크플로우에 RFC 체크 단계 삽입
