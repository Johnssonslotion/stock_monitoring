# ISSUE-048: Market Intelligence & Rotation Analysis Implementation

**Status**: 🔵 Todo
**Priority**: P1 (Alpha Generation)
**Assignee**: Developer
**Created**: 2026-01-29

## 1. Summary
시장 순환매(Sector Rotation) 분석을 위해 외국인/기관 수급 및 공매도 데이터를 수집하고 분석하는 기능을 구현합니다. 이는 v1.0 "Professional Trading Terminal"의 핵심 기능인 Pillar 8에 해당합니다.

## 2. Scope

### 2.1 Backend (Ingestion)
- [ ] KIS Investor TR (`FHKST01010900`, `FHKST03020100`) 연동
- [ ] KIS Short Selling TR (`FHKST02010100`) 연동
- [ ] `history-collector`에 수급 데이터 소급 수집 기능 추가
- [ ] `analysis-worker` (신규) 또는 기존 워커에 수급 데이터 처리 로직 추가

### 2.2 Database
- [ ] `market_investor_trends` 테이블 생성 (Daily/Time-series)
- [ ] `market_short_selling` 테이블 생성

### 2.3 Analysis Logic
- [ ] 섹터별 자금 유입도(Money Flow Index) 계산 로직 구현
- [ ] 수급 집중 종목(외국인/기관 쌍끌이) 매수 탐지 로직

## 3. Implementation Details
- **Data Source**: KIS REST API (Pull 방식)
- **Schedule**: 장 중 매 1시간 또는 장 종료 후 배치 실행

## 4. Verification Plan
- [ ] TR 응답 파싱 유닛 테스트
- [ ] DB 적재 및 조회 성능 테스트
- [ ] HTS 데이터와 비교 검증
