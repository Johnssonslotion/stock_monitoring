# 🚀 환경 분리(Dev/Prod) 전략 및 로드맵

이 로드맵은 로컬 빌드 환경에서도 상용 수준의 안정성과 개발 효율성을 동시에 확보하기 위한 단계별 전환 계획입니다.

## 1. 단계별 로드맵 (Roadmap)

### Phase 1: 설정의 격리 (Configuration Isolation) - *즉시 시행*
- [ ] **`.env` 체계 분리**: 
    - `.env.dev`: 모의투자 키, 테스트용 자산, `dev_` 접두사가 붙은 DB 파일.
    - `.env.prod`: 실전투자 키, 실제 자산, `market_data` 운영 DB.
- [ ] **`.gitignore` 보강**: 실제 운영 키가 포함된 `.env.prod`가 깃에 올라가지 않도록 철저히 차단.

### Phase 2: 오케스트레이션 분리 (Orchestration Separation)
- [ ] **`docker-compose.override.yml` 도입**: 
    - 기본 `docker-compose.yml`에는 공통 서비스(Redis, DB) 정의.
    - `dev.yml`에는 `ticker-gen`(가짜 데이터 생성기) 포함.
    - `prod.yml`에는 `real-collector`(실제 수집기)와 로깅 보안 설정 강화.
- [ ] **명시적 환경 지정**: `Makefile`을 통해 `make up-dev`, `make up-prod`와 같이 실수 없는 실행 구조 구축.

### Phase 3: 데이터 및 볼륨 격리 (Data Isolation)
- [ ] **DB 물리적 분리**: 
    - `data/dev/`와 `data/prod/` 하위 폴더 분리.
    - 개발 중 발생하는 대량의 테스트 틱 데이터가 운영 DB 용량을 점유하지 않도록 관리.
- [ ] **로그 아카이빙**: 운영 환경 로그는 별도 파일로 남겨 장애 분석(RCA)의 근거로 활용.

### Phase 4: 빌드 및 검증 자동화 (Build & Verify)
- [ ] **Local Build Script**: 로컬에서 이미지를 구울 때 자동으로 환경 태그(e.g., `stock-monitoring:dev`, `stock-monitoring:prod`)를 붙여 관리.
- [ ] **Smoke Test**: 운영 환경 배포 전, 수집기가 1분 이내에 데이터를 정상 수집하는지 체크하는 최소한의 헬스체크 도입.

---

## 2. 페르소나별 심층 검토 (Persona Review)

### 👔 PM (Project Manager)
> "환경 분리는 결국 **'실수의 비용'**을 줄이는 투자입니다. 운영 환경(Prod)의 대시보드는 언제든 사용자가 볼 수 있는 '전시용' 상태를 유지해야 하며, 모든 모험적인 시도는 개발 환경(Dev)에서 이루어져야 합니다."

### 🏛️ Architect
> "현재 발생했던 시크릿 유실 장애가 다시는 발생하지 않도록, `HistoryLoader`나 `RealCollector`가 실행될 때 **자신이 어떤 환경(Dev/Prod)에 있는지 로그 상단에 명시**하도록 설계에 반영하겠습니다."

### 🔬 Data Scientist
> "모델링이나 백테스팅 시 Dev 데이터가 섞이면 전체 알고리즘의 신뢰도가 붕괴됩니다. 명시적인 DB 파일 경로 분리는 데이터 사이언스 팀의 필수 요구사항입니다."

### 🔧 Infrastructure Engineer
> "로컬 빌드 상황에서 `env_file`을 쓰기로 한 것은 좋은 시작입니다. 여기에 더해 **네트워크 격리**를 통해 개발 수집기가 운영 Redis 채널을 오염시키지 않도록 설정하겠습니다."

---

## 3. 기대 효과
- **안정성**: 개발 중 실수로 운영 서비스가 중단되는 사태 방지.
- **보안**: 개발 시에는 제한된 권한의 키만 사용함으로써 유출 리스크 최소화.
- **속도**: 가짜 데이터 생성기(`ticker-gen`)를 통해 휴장 시간에도 언제든 대시보드 기능을 개발/테스트 가능.
