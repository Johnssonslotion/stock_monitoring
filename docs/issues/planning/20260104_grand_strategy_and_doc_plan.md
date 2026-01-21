# 종합 문서화 계획 (Documentation Master Plan)

## 목표 설명
제안을 하나씩 던지는 것이 아니라, **Doc Specialist**가 판단한 "엔터프라이즈급 프로젝트에 필요한 모든 문서"를 리스팅하고, 이를 선제적으로 정의합니다. 이 문서들이 갖춰져야만 개발자가 혼란 없이 구현에 집중할 수 있습니다.

## User Review Required
> [!IMPORTANT]
> **Doc Specialist's Manifest**
> "코드는 바뀔 수 있어도, 문서는 남습니다. 다음 문서들은 선택이 아니라 필수입니다."

## 문서 전체 목록 (Documentation Map)

### 1. 근간 (Foundation) - *Completed*
-   `README.md`: 프로젝트 대문.
-   `docs/project_context.md`: 프로젝트의 정의와 맥락.
-   `.ai-rules.md`: 팀의 규율과 페르소나.
-   `docs/grand_strategy.md`: 4단계 대전략.

### 2. 기술 명세 (Technical Specs) - *To Be Created*
-   **[1순위] `docs/data_schema.md` (데이터 스키마 정의서)**
    -   내용: Tick, OrderBook, Candle, Signal의 JSON 필드 타입 정밀 정의.
    -   목적: Data Scientist ↔ Developer 간 데이터 포맷 분쟁 방지.
-   **[1순위] `docs/architecture_design.md` (상세 아키텍처 설계서)**
    -   내용: Redis Pub/Sub 채널명, 모듈 간 데이터 흐름도(Mermaid), 디렉토리 구조 설명.
    -   목적: Architect의 설계를 시각화.

### 3. 품질 및 검증 (Quality & QA) - *To Be Created*
-   **[2순위] `docs/testing_scenarios.md` (테스트 케이스 명세서)**
    -   내용: 정상/비정상/카오스(Chaos) 테스트 시나리오 목록.
    -   목적: QA Engineer의 기준점.
-   **[2순위] `docs/troubleshooting_playbook.md` (장애 조치 플레이북)**
    -   내용: 에러 코드별(1001, 4004 등) 대응 매뉴얼.
    -   목적: Infra/Ops의 생존 가이드.

### 4. 보안 및 운영 (Security & Ops) - *To Be Created*
-   **[3순위] `docs/security_guidelines.md` (보안 가이드라인)**
    -   내용: API Key 관리, `.env` 취급 주의사항, PII(개인정보) 처리 원칙.
    -   목적: 사고 예방.

## Proposed Changes (Immediate Actions)

### [NEW] `docs/data_schema.md`
-   TickData (Source, Normalized), CandleData 정의.

### [NEW] `docs/architecture_design.md`
-   Redis Channel Naming Convention 명시.
-   Asyncio Event Loop Model 설명.

### [NEW] `docs/testing_scenarios.md`
-   Collector, Processor, Trader 모듈별 TC Top 5 정의.

## Verification Plan
### Manual Review
-   사용자가 이 목록을 보고 "이제 빠진 게 없다"고 느낄 때까지 리스팅 보완.
-   문서 스켈레톤 생성 후 커밋.
