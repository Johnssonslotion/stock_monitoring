# ISSUE-012: 상관관계 엔진 (Correlation Engine)

**Status**: Open (작성 완료)
**Priority**: P3 (Analytical)
**Type**: Feature
**Created**: 2026-01-17
**Assignee**: Quant Developer

## 문제 설명 (Problem Description)
가격 상관관계(Pearson Correlation)와 뉴스 키워드 기반으로 연관 종목(`RelatedAssets`)을 자동으로 식별해야 합니다.

## 완료 조건 (Acceptance Criteria)
- [ ] 피어슨 상관관계 알고리즘 구현.
- [ ] 뉴스 키워드 기반 연관성 분석.
- [ ] `RelatedAssets` API 응답 구현.

## 기술 상세 (Technical Details)
- **Library**: `pandas` 또는 `numpy` 활용.
