# Development Standards & Quality Gates

## 1. 협업 프로토콜 (Protocol)
### 1.1 다중 작업 규칙
-   **모듈 격리**: A가 `short_term` 작업 시, B는 `long_term` 작업. (File-level Conflict 방지)
-   **동기화**: 작업 시작 전 `git pull --rebase` 필수.

### 1.2 완료 조건 (Definition of Done)
1.  **동작 검증**: `pytest` 통과.
2.  **정적 분석**: `flake8`, `black` 준수.
3.  **문서화**: 변경된 로직에 대한 Docstring 및 `README` 업데이트.
4.  **Schema Triple-Lock**: 스키마 변경 시 **API Spec + Python Model + DB Migration SQL** 3종 세트 동시 커밋 및 검증 필수. (아카이버의 `init_db`에만 의존 금지)
5.  **DB 마이그레이션**: `migrate.sh` 검증 필수.
6.  **Ground Truth 준수**: 모든 데이터 생성 및 검증 로직은 **[Ground Truth Policy](ground_truth_policy.md)**의 우선순위를 따라야 함. (v2.16+)

### 1.3 멀티 디바이스 및 원격 근무 프로토콜 (Multi-Device Protocol) [v0.02+]
1.  **OS Agnostic**: 모든 스크립트(`Makefile`, `bash`)는 OS를 자동 감지하여 동작해야 한다.
    -   *Rule*: 하드코딩된 경로(`/home/ubuntu`) 금지. 상대 경로(`.` or `$PWD`) 사용.
2.  **Docker First**: 로컬 환경 오염 방지를 위해 모든 실행은 Docker 내에서 수행한다.
3.  **Secret Management**: `.env` 관리 및 `.env.example` 동기화 필수.
4.  **Tailscale Access (SSH Config)**:
    -   **MagicDNS**: Tailscale 사용 시 IP 대신 기기 이름(`monitor-prod`)을 사용할 수 있습니다.
    -   **SSH Config Setup (`~/.ssh/config`)**:
        ```ssh
        Host stock-monitor-prod
            HostName 100.x.y.z
            User ubuntu
        ```
5.  **DB Snapshot Workflow**: `make sync-db-prod`를 통한 실데이터 기반 테스트.

### 1.5 환경별 배포 및 설정 표준 (Environment Standards) [v2.16+]
**원칙**: `Makefile`은 실행 환경(Mac, Linux, 프로젝트 폴더명)을 자동 감지하여 최적의 설정을 적용한다.

| 환경 (ENV_TYPE) | 감지 조건 | 설정 파일 | 포트 (API/Redis) | Docker Compose |
| :--- | :--- | :--- | :--- | :--- |
| **local** | OS = Darwin (Mac) | `.env.local` | 8000 / 6379 | `docker-compose.yml` + `local.yml` |
| **backtest** | Folder = `stock_backtest` | `.env.backtest` | 8002 / 6381 | `docker-compose.yml` + `backtest.yml` |
| **prod** | Linux & `stock_monitoring` | `.env.prod` | 8001 / 6380 | `docker-compose.yml` |

**핵심 명령**:
-   **운영 배포**: `make up-prod`
    -   `.env.prod` 검증(`validate-env-prod`) 및 `preflight_check.sh`가 자동 실행됨.
    -   운영 서버(Linux)에서만 실행해야 하며, 실행 후 `docker system prune`이 자동으로 수행되어 안정성을 확보함.
-   **백테스트 실행**: `make backtest-up`
    -   격리된 전용 포트와 `.env.backtest`를 사용하여 운영 환경과 간섭 없이 대량 연산을 수행함.
-   **환경 확인**: `make identify`
    -   현재 감지된 환경과 적용될 변수를 사전에 확인할 수 있음.

### 1.6 UI 개발 및 원격 접속 전략 (UI & Remote Strategy)
- **GUI는 로컬에서, 로직은 서버에서.**
- **Port Forwarding**: 5173, 8000 등 터널링 사용.
- **E2E 테스트**: 서버/CI 환경에서는 Headless Mode 필수.

## 2. 코딩 및 테스트 표준 (Coding & Testing Standard)

### 2.1 코딩 컨벤션
-   **언어**: Python 3.10+ (Type Hinting 필수).
-   **Docstring**: Google Style (**한국어**).

### 2.2 테스트 환경 및 실행 (Testing Standards) [STRICT]
1.  **Isolated Environment**: 모든 테스트 및 실행은 반드시 **Poetry** 가상환경 내에서 수행한다. (`pip install` 절대 금지)
2.  **Path Resolution**: 패키지 탐색 오류 방지를 위해 모든 실행 시 `PYTHONPATH=.`를 명시한다.
    -   *Example*: `PYTHONPATH=. poetry run pytest tests/`
3.  **Framework**: `pytest`를 기본으로 사용한다.
4.  **Test Tiers**:
    -   `tests/unit/`: 순수 로직 (Logic)
    -   `tests/integration/`: DB/Redis 연동 (Synergy)
    -   `tests/e2e/`: 전체 파이프라인 (Resilience)

### 2.3 시간 처리 표준화 (Time Handling Standard)
1.  **"No-Now" 원칙**: 비즈니스 로직 내부에서 `datetime.now()` 직접 호출 금지.
2.  **Ingestion Gate Pinning**: 진입점에서 생성 후 Dependency Injection.
3.  **UTC First / ISO 8601 준수**.

### 2.4 데이터 정합성 표준 (Data Integrity Standard) [NEW]
1.  **Ground Truth Policy**: 시스템의 모든 데이터는 **[Ground Truth Policy](ground_truth_policy.md)**에 정의된 위계를 따른다.
    -   **REST API 분봉 = 최종 참값**.
    -   틱 집계 데이터는 검증(Volume Check) 완료 후에만 준참값으로 격상된다.
2.  **Centralized API Control**: 모든 KIS/Kiwoom REST API 호출은 `RedisRateLimiter`(`gatekeeper`)를 경유해야 한다.
3.  **Schema Compliance**: 모든 분봉 데이터는 `source_type` 컬럼을 포함하여 출처를 명시해야 한다.

### 2.5 Git Flow
-   Conventional Commits + **Strict Git Flow**.
-   모든 작업은 `feat/...`, `fix/...` 독립 브랜치에서 수행. Mega-Commit 금지.

## 3. 디버깅 및 품질 게이트 (Quality Gate)

### 3.1 통합 테스트 강제 (Integration Test Enforcement)
- 외부 의존성(Redis, DB, API)이 있는 컴포넌트는 실제 연결 테스트 필수.
- "로그 정상" ≠ "데이터 흐름 정상".

### 3.1.5 에러 분석 게이트 (Error Analysis Gate - ZEVS)
- 모든 버그 수정 PR은 이슈 문서의 `Failure Analysis` 섹션 포함 필수.
- Regression Test 포함 및 `test_registry.md` 등록 필수.

### 3.2 Zero Data 알람 (Zero Data Alarm)
- 5분 이상 0건 수집 시 즉시 디버깅 모드 진입 및 알림.

### 3.3 API 문서 확인 (Library Documentation Check)
- 처음 사용하는 라이브러리 메서드는 공식 문서 1회 필수 확인 및 REPL 테스트.

### 3.4 TDD 완성도 등급 (Quality Gate Stages)
- **1단계 (Unit)**: 로직 커버리지 100%.
- **2단계 (Integration)**: DB 적재 일관성 확인.
- **3단계 (E2E)**: Chaos Engineering 및 복구 회복력 확인.

## 4. 단일 진실 공급원 및 보고 의무 (SSoT & Reporting) [STRICT]

### 4.1 개발 표준 문서(development.md) 숙지 의무
- **"No Review, No Work."**
- AI 및 개발자는 매 작업 시작 전 `development.md`를 필독하고 준수 여부를 자가 Audit해야 한다.
- 특히 모델 변경이나 API 연동 시 **DoD(1.2)**와 **Integrity(2.4)** 조항을 최우선 참조한다.

### 4.2 문서 동조화 및 품질 보고서
- **3대 문서**: README, master_roadmap, test_registry 동시 업데이트.
- **품질 보고서**: Unit/Integration/E2E/SSoT 통과 여부 요약 보고.

---
**의무**: AI는 새로운 기능을 구현하거나 설계를 변경할 때, 위 표준의 정합성이 깨지지 않았는지 스스로 Audit하고 보고할 의무가 있다.
