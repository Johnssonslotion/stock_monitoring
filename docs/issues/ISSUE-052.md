# ISSUE-052: Program Trading Collector (Pillar 8)

**Status**: Todo
**Priority**: P1
**Type**: feature
**Created**: 2026-01-29
**Assignee**: Developer
**RFC**: RFC-010

## Problem Description

Pillar 8 Phase 1의 핵심 기능으로, 프로그램 매매(차익/비차익) 데이터를 수집하는 Collector가 필요합니다.

검증 필요 TR ID:
- `FHPTJ04300000`: 종목별 프로그램매매추이
- `FHPTJ04300100`: 프로그램매매 종합현황

> **Note**: TR ID는 RFC-010 추정치이며, 구현 전 Schema Discovery를 통한 검증 필요

## Acceptance Criteria

- [ ] KIS API TR ID 검증 (Schema Discovery)
- [ ] KIS API 클라이언트를 사용한 데이터 수집
- [ ] API 응답을 DB 스키마로 변환
- [ ] program_trading 테이블에 저장 (UPSERT)
- [ ] 배치 수집 기능 (모든 종목)
- [ ] 데몬 모드 (장 마감 후 자동 수집)
- [ ] CLI 인터페이스

## Technical Details

### 수집 데이터 (예상)

| 필드 | API 응답 (추정) | DB 컬럼 |
|------|----------------|---------|
| 차익 매수 | `arbt_buy_qty` | `arb_buy` |
| 차익 매도 | `arbt_seln_qty` | `arb_sell` |
| 차익 순매수 | `arbt_ntby_qty` | `arb_net` |
| 비차익 매수 | `narbt_buy_qty` | `non_arb_buy` |
| 비차익 매도 | `narbt_seln_qty` | `non_arb_sell` |
| 비차익 순매수 | `narbt_ntby_qty` | `non_arb_net` |
| 전체 순매수 | `pgmg_ntby_qty` | `total_net` |

### 파일 구조

```
src/data_ingestion/intelligence/
├── __init__.py
├── investor_trends_collector.py  # 완료
├── short_selling_collector.py    # ISSUE-051
└── program_trading_collector.py  # 신규
```

### 사용법 (예정)

```bash
# 1회 실행 (테스트)
python -m src.data_ingestion.intelligence.program_trading_collector --once

# 단일 종목
python -m src.data_ingestion.intelligence.program_trading_collector --symbol 005930

# 데몬 모드 (장 마감 후 자동)
python -m src.data_ingestion.intelligence.program_trading_collector
```

## Implementation Notes

1. `InvestorTrendsCollector` 패턴을 따름
2. TR ID 검증 후 실제 응답 스키마에 맞게 transform 로직 구현
3. 차익/비차익 순매수 방향성 분석 기능 추가 예정

## Related

- Branch: `feature/pillar8-market-intelligence`
- RFC: [RFC-010](../governance/rfc/RFC-010-market-intelligence-pillar8.md)
- DB Migration: `sql/migrations/007_pillar8_market_intelligence.sql`
- Depends on: ISSUE-049 (TR ID 검증)
- Blocks: ISSUE-055 (Sector Rotation Detector)
