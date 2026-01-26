# ISSUE-043: Upgrade RealtimeVerifier to OHLCV Aggregation Logic

**Status**: Open
**Priority**: P1 (High)
**Type**: Bug (Implementation Gap) - Missed Requirement from RFC-008
**Created**: 2026-01-26
**Assignee**: Agent

## 1. 개요 (Problem Description)
현재 `RealtimeVerifier`는 **거래량(Volume) 합계**만을 단순 비교하고 있어, 가격 데이터(Price)의 무결성을 보장하지 못함.
사용자는 로컬에 수집된 **틱 데이터(Tick)를 직접 1분봉(OHLCV)으로 합산(Aggregation)**하여, 브로커 API의 공식 분봉과 정밀 대조하기를 원함.


- **History**: `RFC-008: Appendix C.2 Option B (ADOPTED)`에서 이미 "OHLCV Consistency (정밀 검증)" 전략이 승인됨.
- **Current**: `Local DB Volume Sum` vs `API Volume` (2% tolerance) - Tier 1만 구현된 상태.
- **Required**: `Local Tick Aggregation (OHLCV)` vs `API Candle (OHLCV)` - Tier 2 구현 누락분.

## 2. 상세 구현 계획 (Technical Details)

### 2.1. DB 스키마 설계 (Schema Design)
`market_verification_results` 테이블을 확장하여 가격 검증 결과를 포함합니다.

| Field | Type | Description |
| :--- | :--- | :--- |
| `time` | timestamp | 검증 대상 분 (PK) |
| `symbol` | text | 종목 코드 (PK) |
| `local_vol` | double | **[New]** 로컬 DB 집계 거래량 (Tick Sum) |
| `api_vol` | double | API 조회 거래량 (Renamed from kis_vol/kiwoom_vol) |
| `price_match` | boolean | **[New]** 가격(OHLC) 완전 일치 여부 |
| `details` | jsonb | **[New]** 불일치 상세 (예: `{"high_diff": -100, "local": [100, 102, 99, 101]}`) |
| `status` | text | `PASS` / `FAIL` / `RECOVERING` |

### 2.2. 로직 흐름 (Operation Flow)
1. **Local Aggregation (TimescaleDB)**
   - `market_ticks` 테이블에서 `first(price, time)`, `max(price)`, `min(price)`, `last(price, time)`, `sum(volume)` 쿼리.
2. **API Fetch (API Hub)**
   - KIS/Kiwoom REST API를 통해 해당 분의 공식 1분봉(OHLCV) 조회.
3. **Comparison Logic**
   - **Price (OHLC)**: **Strict Match** (부동소수점 오차 `1e-9` 미만 허용). 하나라도 다르면 `FAIL`.
   - **Volume**: 기존 허용오차(Tolerance) **2%** 유지.
4. **Action**
   - 불일치 발생 시 `FAIL` 기록 및 **즉시 Recovery Queue**에 복구 작업 등록.

## 3. 완료 조건 (Acceptance Criteria)
- [ ] `RealtimeVerifier`가 TimescaleDB의 집계 함수(`first`, `last`)를 사용하여 로컬 캔들을 생성해야 함.
- [ ] 가격(Price) 불일치 시, 거래량이 맞더라도 `NEEDS_RECOVERY` 상태로 전이되어야 함.
- [ ] `market_verification_results` 테이블에 `price_match`, `details` 컬럼이 추가되고 데이터가 적재되어야 함.

## 4. Related
- **Origin**: [RFC-008](../governance/rfc/RFC-008-tick-completeness-qa.md#c2-최종-verification-strategy) (Option B: Volume + OHLCV Cross-Check)
- [ISSUE-042](ISSUE-042.md) (Network Isolation Fix)
