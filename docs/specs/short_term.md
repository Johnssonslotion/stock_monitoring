# 단기 전략 명세서 (Short-term Strategy Spec)

**작성일**: 2026-01-04
**담당자**: Doc Specialist & Architect

## 1. 개요
실시간 **틱(Tick) 데이터**를 수집하여 초단기 시장의 비효율성을 포착하고, **스캘핑(Scalping)** 또는 데이트레이딩 전략을 수행한다.

## 2. 데이터 수집 (Data Ingestion)
### 2.1 대상 자산
-   **시장**: 국내 주식(KOSPI/KOSDAQ) 또는 해외 선물 (API 접근성에 따라 결정).
-   **종목 선정**: 거래량 상위 TOP 10 종목 (유동성 풍부한 종목).

### 2.2 수집 방식
-   **프로토콜**: Websocket 사용 (지연 시간 최소화).
-   **데이터 형태**: `(Timestamp, Price, Volume, Bid/Ask)`
-   **보관**: 당일 데이터는 메모리(Redis/Queue)에 유지, 장 마감 후 폐기 또는 압축 저장.

## 3. 분석 로직 (Analysis)
### 3.1 기술적 지표 (Indicators)
-   **이격도**: 이동평균선과 현재가의 괴리율 활용.
-   **Order Book Imbalance (OIB)**: 매수 호가 잔량 vs 매도 호가 잔량의 불균형 포착.
-   **VP (Volume Profile)**: 가격대별 거래량 분석.

## 4. 전략 실행 (Execution)
### 4.1 진입/청산 규칙
-   **진입 (Entry)**: OIB가 급격히 한쪽으로 쏠릴 때 추세 추종 (Momentum).
-   **청산 (Exit)**:
    -   **익절**: 목표 수익률 (+0.5% ~ 1.0%) 도달 시 즉시 청산.
    -   **손절**: 반대 방향 틱 발생 시 즉시 청산 (Trailing Stop).

### 4.2 리스크 관리
-   **슬리피지(Slippage) 제어**: 시장가(Market) 주문보다는 지정가(Limit) 주문 우선.
-   **1일 손실 한도**: 자산의 2% 손실 시 당일 거래 중지.

## 5. 시스템 요구사항
-   **Latency**: 수집부터 주문까지 100ms 이내 목표 (Python 비동기 처리 `asyncio` 필수).
