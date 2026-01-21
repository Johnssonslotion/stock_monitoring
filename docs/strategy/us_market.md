# US Market Data Collection Strategy

미국 시장(US Market)의 틱 및 히스토리 데이터를 효율적으로 수집하기 위한 전략입니다.

## 1. 개요
미국 시장은 한국 시장과 달리 무료 데이터 소스(yfinance 등)가 풍부하지만, 실시간 시세(WebSocket)의 경우 한국투자증권(KIS)과 같은 국내 브로커 API를 활용하는 것이 연동 편의성 면에서 유리합니다.

## 2. 데이터 수집 단계 (Phases)

### Phase 1: 분석 및 백테스트용 데이터 수집 (yfinance)
- **목적**: 과거 데이터 확보 및 장 종료 후 일일 마감 데이터 동기화.
- **도구**: `yfinance` 라이브러리.
- **수집 주기**: 
    - 장 종료 후 1회 (Daily/Intraday 1m).
    - 시뮬레이션 및 백테스트 필요 시 호출.
- **장점**: 구현이 매우 빠르고 무료이며, 전 세계 대부분의 ETF/주식 지원.

### Phase 2: 실시간 데이터 수집 (KIS API)
- **목적**: 실시간 가격 변동 모니터링 및 알람.
- **도구**: KIS 해외 주식 WebSocket API.
- **수집 대상**: `configs/market_symbols.yaml`의 `us` 섹션에 정의된 심볼 (SPY, QQQ, TQQQ 등).
- **구현 계획**:
    - `real_collector.py`에 해외 주식용 WebSocket 엔드포인트(`ops.koreainvestment.com:443`) 연동 추가.
    - 한국/미국 시장 운영 시간에 따른 동적 스케줄링.

## 3. 기술적 고려사항
- **시차 관리**: 미국 시장(EST)과 한국 시간(KST) 간의 변환을 철저히 관리 (Summer Time 고려).
- **심볼 포맷**: KIS API의 경우 미국 시장 심볼 앞에 거래소 구분자(예: NAS, NYS)가 필요할 수 있음.
- **비용 최적화**: KIS 실시간 시세는 계좌 등급에 따라 유료일 수 있으므로, 필요 시 지연 시세(Delayed) 활용 검토.

## 4. 실행 계획
1.  `src/data_ingestion/history/us_loader.py` (yfinance 기반) 구현 시작.
2.  `real_collector.py`를 멀티 마켓(Multi-market) 지원 구조로 리팩토링.
