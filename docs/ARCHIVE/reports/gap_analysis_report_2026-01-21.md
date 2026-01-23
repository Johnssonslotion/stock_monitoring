# Gap Analysis Report (2026-01-21)

## 1. 개요 (Overview)
본 보고서는 KIS 서비스 핫픽스 및 ISSUE-036(DB 통합) 작업 이후 수행된 코드-문서 정합성 분석 결과입니다.

## 2. 정합성 불일치 항목 (Inconsistencies)

### 2.1 Archiver Metadata 누락 (Critical)
- **대상**: `src/data_ingestion/archiver/timescale_archiver.py`
- **현상**: `save_orderbook` 메서드에서 `market_orderbook` 테이블에 데이터를 인입할 때, 메타데이터 필드(`broker`, `broker_time`, `received_time`, `sequence_number`)를 저장하지 않음.
- **영향**: 호가 데이터의 지연시간 분석 및 중복 제거 불가.
- **비고**: `market_ticks`는 정상적으로 메타데이터를 포함하여 저장 중임.

### 2.2 실시간 수집 전략 문서 미갱신
- **대상**: `docs/strategy/realtime_ingestion_strategy.md`
- **현상**: 한국 시장(KR)의 TR_ID(`H0STCNT0`)가 "Unverified (추정)" 상태로 기재되어 있음.
- **현실**: 금일 핫픽스를 통해 실시간 수집 성공을 검증 완료함.

### 2.3 DB 스키마-코멘트 미흡
- **대상**: `migrations/001_create_market_ticks.sql`, `002_create_market_orderbook.sql`
- **현상**: 테이블 및 컬럼에 대한 상세 COMMENT가 누락됨 (Goverance Rule #7 준수 필요).

## 3. 거버넌스 위반 (Governance Violations)
- **Hardcoding**: `kis_main.py` 내의 일부 URL 생성 로직에서 `KIS_WS_URL` 상수가 사용되나, 브로커별 분리된 설정 관리가 더 권장됨. (현재는 수용 가능한 수준)

## 4. 권장 조치 (Recommendations)
1. **[P0]** `TimescaleArchiver.save_orderbook` 수정: 메타데이터 4종 필드 저장 로직 추가.
2. **[P1]** `realtime_ingestion_strategy.md` 업데이트: KR 마케 검증 완료 및 성공 구성값(Config) 반영.
3. **[P2]** 마이그레이션 SQL에 `COMMENT ON TABLE/COLUMN` 추가.

## 5. 결론 (Conclusion)
전반적인 스키마 정합성은 양호하나, **Orderbook 메타데이터 누락**은 데이터 분석 품질에 영향을 미치므로 즉시 수정이 필요합니다.
