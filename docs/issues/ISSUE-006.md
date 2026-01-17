# ISSUE-006: 시장 섹터 서비스 (Market Sector Service)

**Status**: Open (작성 완료)
**Priority**: P2 (Major)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Data Engineer

## 문제 설명 (Problem Description)
실시간 시장 섹터 성과(예: 반도체, 바이오)를 계산하고 제공해야 합니다. 구성 종목들의 수익률을 집계하는 배치 작업이 필요합니다.

## 완료 조건 (Acceptance Criteria)
- [ ] 10초 주기의 섹터 등락률 집계 배치(Batch) 작업.
- [ ] `GET /api/market/sectors` 엔드포인트 구현.

## 기술 상세 (Technical Details)
- **Computation**: 구성 종목의 가중 평균 수익률 계산.
