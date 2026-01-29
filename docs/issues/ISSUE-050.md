# ISSUE-050: Investor Trends Collector (Pillar 8)

**Status**: Done
**Priority**: P1
**Type**: feature
**Created**: 2026-01-29
**Completed**: 2026-01-29
**Assignee**: Developer
**RFC**: RFC-010

## Problem Description

Pillar 8 Phase 1의 핵심 기능으로, 투자자별(외국인/기관/개인) 매매동향 데이터를 수집하는 Collector가 필요합니다.

검증 완료된 TR ID:
- `FHKST01010900`: 주식현재가 투자자

## Acceptance Criteria

- [x] KIS API 클라이언트를 사용한 데이터 수집
- [x] API 응답을 DB 스키마로 변환
- [x] investor_trends 테이블에 저장 (UPSERT)
- [x] 배치 수집 기능 (모든 종목)
- [x] 데몬 모드 (장 마감 후 자동 수집)
- [x] CLI 인터페이스

## Technical Details

### 수집 데이터

| 필드 | API 응답 | DB 컬럼 |
|------|----------|---------|
| 외국인 순매수량 | `frgn_ntby_qty` | `foreign_net` |
| 기관 순매수량 | `orgn_ntby_qty` | `institution_net` |
| 개인 순매수량 | `prsn_ntby_qty` | `retail_net` |
| 외국인 매수량 | `frgn_shnu_vol` | `foreign_buy` |
| 외국인 매도량 | `frgn_seln_vol` | `foreign_sell` |
| 기관 매수량 | `orgn_shnu_vol` | `institution_buy` |
| 기관 매도량 | `orgn_seln_vol` | `institution_sell` |
| 개인 매수량 | `prsn_shnu_vol` | `retail_buy` |
| 개인 매도량 | `prsn_seln_vol` | `retail_sell` |

### 파일 구조

```
src/data_ingestion/intelligence/
├── __init__.py
└── investor_trends_collector.py
```

### 사용법

```bash
# 1회 실행 (테스트)
python -m src.data_ingestion.intelligence.investor_trends_collector --once

# 단일 종목
python -m src.data_ingestion.intelligence.investor_trends_collector --symbol 005930

# 데몬 모드 (장 마감 후 자동)
python -m src.data_ingestion.intelligence.investor_trends_collector
```

## Resolution

`InvestorTrendsCollector` 클래스 구현 완료:
- KIS API `FHKST01010900` TR ID 사용
- API 응답 → DB 스키마 변환 로직
- asyncpg를 사용한 배치 저장
- 장 마감 후(15:40 KST) 자동 수집 스케줄링

## Related

- Branch: `feature/pillar8-market-intelligence`
- RFC: [RFC-010](../governance/rfc/RFC-010-market-intelligence-pillar8.md)
- DB Migration: `sql/migrations/007_pillar8_market_intelligence.sql`
- Blocks: ISSUE-054 (Money Flow Index Calculator)
