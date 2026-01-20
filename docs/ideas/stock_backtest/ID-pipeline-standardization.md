# IDEA: 데이터 파이프라인 채널 및 스키마 표준화
**Status**: 💡 Seed (Idea)
**Priority**: P2

## 1. 개요 (Abstract)
- **문제**: 현재 KIS는 `ticker.kr`, Kiwoom은 `tick:KR:{symbol}`과 같이 서로 다른 Redis 채널 규칙을 사용하고 있음. 또한 아카이버는 `ticker.*`만 구독하는 등 파이프라인 간섭 및 데이터 누락이 발생함.
- **기회**: 전사적인 Redis 채널 명명 규칙(Convention)을 수립하고, 모든 수집기가 이를 준수하도록 리팩토링하여 아카이버 및 모니터링 모듈의 복잡도를 낮춤.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: `market:tick:KR:{symbol}`와 같이 계층적인 채널 구조를 도입하면, 아카이버가 `market:tick:*` 만으로 모든 브로커의 데이터를 수용할 수 있으며 데이터 유실 위험이 감소함.
- **기대 효과**:
    - 새로운 수집기 추가 시 아카이버 수정 없이 즉시 저장 가능.
    - 채널 명 매핑 관리 포인트 단일화.

## 3. 구체화 세션 (Elaboration)
- **Backend Engineer**: `BaseCollector`에서 채널 생성 로직을 템플릿화하여 하위 클래스가 마음대로 채널명을 정하지 못하게 강제해야 함.
- **Data Engineer**: Orderbook 데이터 역시 `market:hoga:KR:{symbol}` 등으로 통일하여 `0D`와 `H0STASP0` 데이터를 동일 파이프라인에서 처리.

## 4. 로드맵 연동 시나리오
- **Pillar 3: High Reliability**의 "Standardized Communication Protocol" 과제로 통합.
