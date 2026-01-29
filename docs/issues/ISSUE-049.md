# ISSUE-049: 10단계 호가 수집 확장 및 델타 압축 도입

## Context
사용자 요구사항에 따라 기존 5단계 호가를 10단계로 확장하고, 효율성을 위해 델타 압축을 도입해야 함. 또한 미국 주식은 체결가 위주 모니터링을 유지하며, 한국 주식은 키움을 통해 10단계 호가를 수집함.

## Goals
- [x] 한국 주식(Kiwoom) 10단계 호가 수집 구현
- [x] `OrderbookDeltaFilter` 도입으로 중복 데이터 저장 방지
- [x] 단위 테스트 작성 및 검증 (`tests/unit/test_delta_filter.py`, `tests/unit/test_kiwoom_orderbook.py`)
- [ ] 브랜치 커밋 및 병합

## Specs
- **Broker**: Kiwoom
- **Filter**: Delta-based (Price/Volume change detection)
- **Depth**: 10 levels (Ask/Bid)
