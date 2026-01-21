# IDEA: 단일 키 환경을 위한 데이터 접근 일원화 (Single-Key Governance)
**Status**: 💡 Seed (Idea)
**Priority**: P0 (Immediate)

## 1. 개요 (Abstract)
API Key가 하나뿐인 환경에서 **수집기(Collector)**와 **백테스트/가상매매(Engine)**가 동시에 브로커 API를 호출하여 발생할 수 있는 충돌(Rate Limit, 중복 접속 차단)을 방지하기 위해, **Engine의 API 직접 접근을 물리적으로 차단**하고 오직 데이터 레이크(DB/Redis)를 통해서만 데이터를 소비하도록 강제하는 아키텍처를 수립합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설 1 (Physical Segregation)**: Backtest 환경 변수(`.env.backtest`)에서 API Key를 제거하여 자동화된 엔신의 우발적 접근 차단.
- **가설 2 (Time-Division Multiplexing)**: "장은 피하라". 개발자의 직접적인 API 검증(스키마 확인, 잔고 조회 등)은 **KR/US 정규장 운영 시간**을 피해 수행하도록 `MarketGuard` 유틸리티로 강제한다.
- **가설 3 (Schema Caching)**: 백테스트에 필요한 메타데이터(마스터 종목 정보, 호가 단위 등)는 장 마감 후 **Static File(JSON/SQLite)**로 덤프하여, 장중에는 API 호출 없이 이 캐시를 참조한다.

## 3. 구체화 세션 (Elaboration)
- **Architect (Safe Access Strategy)**:
    - **Physical Lock**:
        - `real-collector`: Always has Key.
        - `backtest-engine`: No Key.
    - **Temporal Lock (MarketAwareGuard)**:
        - `diagnostic_*.py` 실행 시 **Dual-Zone Check** 수행.
        - **KR Block**: 08:30 ~ 16:00 (KST) - 장전/장후 동시호가 포함.
        - **US Block**: 
            - Winter: 23:20 ~ 06:10 (KST)
            - Summer (DST): 22:20 ~ 05:10 (KST)
            - `pytz` 라이브러리를 통해 `America/New_York` 시간대를 실시간 변환하여 DST 자동 처리.
        - **Holiday**: `holidays` 패키지 또는 `market_calendar.yaml`을 참조하여 휴장일에는 실행 허용.
        - **Rule**: `is_kr_open or is_us_open`이면 `SystemExit`.
    - **Metadata Decoupling**:
        - `MasterLoader`: 매일 아침 08:00에 종목 마스터/호가 단위를 긁어서 `data/meta/`에 저장.
        - 백테스팅 엔진은 API 대신 `data/meta/`의 파일을 로드하여 정합성 검증.
- **Developer**:
    - 코드 레벨에서 `KIS_APP_KEY`가 없으면 `BrokerAPI` 클래스 초기화 자체가 실패하도록 설계되어 있으므로, 백테스트 엔진 구동 시 "API 모드"가 아닌 "DB 모드"로만 동작하게 강제됨.

## 4. 로드맵 연동 시나리오
- **Pillar**: Pillar 1 (Infra Stability) & Pillar 6 (Virtual Exchange)
- **Action Item**: `docker-compose.yml`에서 서비스별 `.env` 파일 매핑 분리 및 백테스트 컨테이너의 Outbound Internet Access 제한(Optional).

## 5. 제안하는 다음 단계
1. **Env Split**: `real-collector`는 `.env.prod`, `backtest-engine`은 `.env.backtest`를 쓰도록 명시.
2. **Refactoring**: Backtest Engine이 Broker API Client를 인스턴스화하려는 시도를 감지하여 차단하는 로직 구현.
