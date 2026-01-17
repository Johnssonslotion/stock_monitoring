# ISSUE-005: 데이터 누락 감지 및 채우기 로직 (Data Gap Detection & Filling Logic)

**Status**: Open (작성 완료)
**Priority**: P2 (Medium)
**Type**: Data Quality
**Created**: 2026-01-17
**Assignee**: Data Engineer

## 문제 설명 (Problem Description)
네트워크 장애나 유동성 부족으로 인해 시장 데이터에 누락(Gap)이 종종 발생합니다. API는 이러한 누락을 감지하고, 선택적으로 이전 종가로 채우는(Zero-Order Hold) 로직을 통해 연속적인 차트 경험을 제공해야 합니다.

## 완료 조건 (Acceptance Criteria)
- [ ] `get_candles` 로직에서 누락된 타임스탬프 감지.
- [ ] Zero-Order Hold (직전 종가 채우기) 구현.
- [ ] 응답 메타데이터에 `is_filled` 플래그 추가.

## 기술 상세 (Technical Details)
- **API**: `src/backend/api/candles.py`
- **Algorithm**: 예상 타임스탬프와 실제 타임스탬프 비교.
