# Issue-023: [Bug] TimescaleArchiver Kiwoom 채널 구독 누락 수정

**Status**: Open  
**Priority**: P1  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- `KiwoomWSCollector`는 `tick:KR:*` 채널을 사용하나, `TimescaleArchiver`는 `ticker.*`만 구독하고 있어 Kiwoom 데이터가 TimescaleDB에 누락됨.

## Acceptance Criteria
- [ ] `TimescaleArchiver`의 구독 채널 리스트에 `tick:*` 및 `orderbook:*` 정규 표현식 추가.
- [ ] KIS/Kiwoom 데이터가 동시에 TimescaleDB에 저장되는지 확인.
