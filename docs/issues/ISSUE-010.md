# ISSUE-010: 캔들 데이터 서비스 (Candle Data Service)

**Status**: Open (작성 완료)
**Priority**: P2 (Major)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## 문제 설명 (Problem Description)
과거 캔들 데이터를 REST API(`GET /api/candles`)를 통해 제공해야 합니다. 다양한 타임프레임(분/일/주)을 지원하고 TimescaleDB에서 효율적으로 조회해야 합니다.

## 완료 조건 (Acceptance Criteria)
- [ ] `GET /api/candles` 엔드포인트 구현.
- [ ] 1m, 5m, 1h, 1d, 1w 간격 지원.
- [ ] 성능: 표준 범위 조회 시 응답 시간 < 100ms.

## 기술 상세 (Technical Details)
- **DB**: TimescaleDB
- **Integration**: ISSUE-005 (Gap Handling)와 연동 필요.
