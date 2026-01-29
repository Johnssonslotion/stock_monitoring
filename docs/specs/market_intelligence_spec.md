# Market Intelligence & Rotation Analysis Specification

## 1. 개요 (Overview)
본 명세서는 공매도, 외국인/기관 수급 데이터를 활용하여 업종 간 **순환매(Sector Rotation)**를 탐지하고 포착하는 로직의 기술적 상세를 정의합니다. (v1.0 Pillar 8)

## 2. 데이터 소립 (Data Granularity)
- **Daily Batch**: 장 마감 후 전 종목의 일별 수급 및 공매도 데이터 확정 (SSoT).
- **Intraday Snapshot**: 장 중 1시간 간격으로 투자자별 매매 추이 및 프로그램 매미 현황 모니터링.

## 3. 핵심 분석 로직 (Analysis Logic)

### 3.1 수급 강도 (Money Flow Intensity, MFI)
특정 종목 또는 섹터의 자금 유입 정도를 측정합니다.
- **Formula**: `(외국인순매수대금 + 기관순매수대금) / 시가총액`
- **Threshold**: MFI > 0.5% (강한 유입), MFI < -0.5% (강한 유출)

### 3.2 순환매 점수 (Rotation Score)
섹터 전체의 이동 평균 수급 강도를 기반으로 자금이 어디서 어디로 흐르는지 계측합니다.
1. **Source Sector Identification**: 수급 강도가 하락하며 주가가 횡보/하락하는 섹터.
2. **Target Sector Identification**: 수급 강도가 급증하며 거래량이 동반되는 섹터.
3. **Signal**: Target Sector의 MFI가 최근 5일 평균 대비 2표준편차(σ) 이상 상향 돌파 시 '순환매 발생'으로 플래깅.

### 3.3 공매도 & 숏커버링 분석
- **Short Pressure**: `일일 공매도 거래량 / 전체 거래량` 비율이 20% 초과 시 주의.
- **Short Squeeze Signal**: 공매도 잔고가 높은 상태에서 기관의 강한 매수세가 유입되며 직전 고점을 돌파할 때.

## 4. 데이터베이스 연동
- **`market_investor_trends`**: 일별 순매수 수량 및 비중 저장.
- **`market_short_selling`**: 거래량 및 잔고 데이터 저장.

## 5. 시각화 요구사항 (UI Integration)
- **Sector Heatmap Overlay**: 섹터 맵 위에 수급 강도를 색상(Blue-Red)으로 오버레이.
- **Trend Chart**: 캔들 차트 하단에 외국인/기관 보유 비중 추이 보조 지표 추가.

## 6. 향후 확장 (Next Steps)
- 프로그램 매매 비차익 순매수 실시간 알림 기능.
- 테마주 군집화(Clustering)를 통한 테마별 순환매 추적.
