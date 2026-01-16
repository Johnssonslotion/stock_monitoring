# 브로커별 공식 테스트(모의투자) 환경

## 1. 엔드포인트 정보
- **키움 RE**: `wss://mockapi.kiwoom.com:10000` (KRX 전용)
- **한국투자 (KIS)**: `ops.koreainvestment.com:21000` (모의투자용 포트)
- **미래에셋**: `wss://ws.mstock.trade` (모의 테스트 파라미터 포함)

## 2. 검증 전략
- **Phase 1 (Mock)**: 샘플 패킷을 활용한 오프라인 로직 검증.
- **Phase 2 (Sandbox)**: 실제 공식 테스트 소켓 연결을 통한 흐름(Flow) 검증.
- **모델 검증**: 수신 패킷의 Pydantic Schema 정합성 확인.
