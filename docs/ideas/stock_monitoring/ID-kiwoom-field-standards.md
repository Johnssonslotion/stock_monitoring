# IDEA: Kiwoom Data Field Standardization & Opening QA Strategy
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1

## 1. 개요 (Abstract)
Kiwoom WebSocket 데이터의 필드 비일관성(체결시간 `20` vs 호가시간 `21`)으로 인한 데이터 누락 판단 오류를 방지하기 위해 **엄격한 필드 매핑 및 파싱 표준**을 수립한다. 또한, 장 시작(Opening) 구간의 데이터 무결성을 검증하기 위해 **Kiwoom REST API(분봉/체결)와 WebSocket 집계 데이터 간의 교차 검증 프로세스**를 도입한다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 
    1. 데이터 타입(Tick vs Orderbook)별로 서로 다른 시간 필드(`20`, `21`)를 명시한 `Schema Registry`를 운영하면 파싱 오류를 0%로 줄일 수 있다.
    2. 장 종료 후 Kiwoom REST API로 '1분봉' 데이터를 조회하여, 수집된 WebSocket 틱 데이터를 1분 단위로 집계한 결과와 비교하면 데이터 유실을 정확히 탐지할 수 있다.
- **기대 효과**:
    - "False Alarm"(허위 장애 보고) 방지.
    - 골든 소스(Kiwoom)에 대한 신뢰도에 수학적 근거 마련 (일치율 99.9% 입증).

## 3. 구체화 세션 (Elaboration)
- **Developer**: "현재 `verify_opening.py` 같은 임시 스크립트가 아니라, `KiwoomLogParser` 클래스를 만들어 필드 매핑(`field_20=trade_time`, `field_21=hoga_time`)을 중앙화해야 함."
- **Data Scientist**: "오프닝 검증은 '틱 갯수'만으로는 부족함. Kiwoom REST API(`opt10080`: 주식분봉차트조회)를 통해 09:00~09:05의 **Core 40 종목 거래량 합계**를 가져와, 우리가 수집한 틱 거래량 합계와 비교하는 `Volume Delta Check`가 필요함."
- **QA**: "QA 워크플로우 실행 시 이 문서(`ID-kiwoom-field-standards.md`)의 체크리스트를 강제로 확인하도록 만듭시다."

## 4. 로드맵 연동 시나리오
- **Pillar**: Reliability & Quality Assurance
- **Action Item**: 
    1. `src/data_ingestion/parsing/kiwoom_schema.py` 작성 (필드 정의).
    2. `scripts/quality/cross_validate_volume.py` 작성 (REST `opt10080` 거래량 비교).
    3. **[NEW] `scripts/quality/verify_tick_counts.py` 작성 (REST `opt10079` 틱수 비교)**.
       - TR Code: `opt10079` (주식틱차트조회)
       - Logic: API 리턴 `체결건수` vs DB `COUNT(*)` 비교.
