# Development Standards & Quality Gates

## 1. 협업 프로토콜 (Protocol)
### 1.1 다중 작업 규칙
-   **모듈 격리**: A가 `short_term` 작업 시, B는 `long_term` 작업. (File-level Conflict 방지)
-   **동기화**: 작업 시작 전 `git pull --rebase` 필수.

### 1.2 완료 조건 (Definition of Done)
1.  **동작 검증**: `pytest` 통과.
2.  **정적 분석**: `flake8`, `black` 준수.
3.  **문서화**: 변경된 로직에 대한 Docstring 및 `README` 업데이트.
4.  **DB 마이그레이션**: 스키마 변경 시 `migrate.sh` 검증 및 SQL 파일 커밋 필수.

### 1.3 멀티 디바이스 및 원격 근무 프로토콜 (Multi-Device Protocol) [v0.02+]
**배경**: Mac(Apple Silicon), Linux(Server), Windows 등 이기종 환경에서의 동시 작업을 지원한다.

1.  **OS Agnostic**: 모든 스크립트(`Makefile`, `bash`)는 OS를 자동 감지하여 동작해야 한다.
    -   *Rule*: 하드코딩된 경로(`/home/ubuntu`) 금지. 상대 경로(`.` or `$PWD`) 사용.
2.  **Docker First**: 로컬 환경 오염 방지를 위해 모든 실행은 Docker 내에서 수행한다.
    -   *Mac User*: `deploy/docker-compose.local.yml` (Volume Mount, Port Mapping 최적화) 사용.
    -   *Server*: `deploy/docker-compose.yml` (Resource Limit, Restart Policy) 사용.
3.  **Secret Management**:
    -   `.env` 파일은 절대 공유하지 않는다. (Git Ignore)
    -   새로운 키 추가 시 `.env.example` 동기화 필수.
    -   장비 간 이동 시 Secrets Manager(1Password 등)나 보안 채널을 통해 개별 주입.
4.  **Tailscale Access (SSH Config)**:
    -   **MagicDNS**: Tailscale 사용 시 IP 대신 기기 이름(`monitor-prod`)을 사용할 수 있습니다.
    -   **SSH Config Setup (`~/.ssh/config`)**:
        ```ssh
        # ~/.ssh/config 예시
        Host stock-monitor-prod
            HostName 100.x.y.z  # Tailscale IP 또는 MagicDNS 이름
            User ubuntu
            IdentityFile ~/.ssh/id_rsa_stock
        ```
    -   *Makefile*: 위 설정이 되어 있다면 `make sync-db-prod` 실행 시 자동으로 연결됩니다.
    -   *Override*: 설정이 다르다면 `make sync-db-prod PROD_HOST=my-server`로 실행 가능합니다.

5.  **DB Snapshot Workflow ("임시 DB 떠오기")**:
    -   **목적**: 로컬 개발 시 '빈 깡통 DB'가 아닌 '실제 데이터' 기반으로 테스트하기 위함.
    -   **Command**: `make sync-db-prod` (구현 예정)
    -   **Logic**: `ssh | pg_dump | gunzip | psql` 스트리밍 파이프라인 사용.
    -   **Note**: 대용량 데이터 전송 시 비용 발생 주의(Outbound Traffic). 필요 시 `pg_dump`에 `--schema-only` 또는 `LIMIT` 옵션 사용 고려.

### 1.4 UI 개발 및 원격 접속 전략 (UI & Remote Strategy)
**"GUI는 로컬에서, 로직은 서버에서."**

1.  **Web Dashboard**:
    -   SSH 환경에서는 브라우저 실행이 불가능하므로, **Port Forwarding**을 사용한다.
    -   *Cmd*: `ssh -L 5173:localhost:5173 -L 8000:localhost:8000 monitor-prod`
    -   *Access*: 로컬 브라우저에서 `localhost:5173` 접속.
2.  **Electron App**:
    -   **실행 위치**: 반드시 **로컬 머신(Mac/Windows)**에서 실행한다. (SSH X11 Forwarding 금지)
    -   **Hybrid Dev**: 로컬 앱이 **원격 백엔드(Remote API)**를 바라보게 설정한다.
        -   `VITE_API_URL=http://localhost:8000` (w/ Tunnel)
3.  **Browser Automation (E2E)**:
    -   서버/CI 환경에서는 반드시 **Headless Mode**(`--headless`)로 구동한다.

## 2. 코딩 컨벤션 (Coding Standard)
-   **언어**: Python 3.10+ (Type Hinting 필수).
-   **Docstring**: Google Style (`Args`, `Returns`, `Raises` 명시). 언어는 **한국어**.
    ```python
    def collect_ticks(symbol: str) -> None:
        """
        거래소에서 틱 데이터를 수집하여 Redis Pub/Sub으로 전송한다.

        Args:
            symbol (str): 수집 대상 심볼 (예: 'KRW-BTC')
        """
    ```
-   **Git**: Conventional Commits + **Strict Git Flow**.
    -   **Rule**: 모든 작업은 `develop`에서 파생된 독립적인 **Feature Branch**(`feat/...`, `fix/...`)에서 수행해야 한다.
    -   **Prohibited**: `develop` 브랜치에 직접 커밋하거나, 여러 피쳐를 하나의 브랜치에 섞는 행위(Mega-Commit)는 엄격히 금지된다.
    -   **Workflow**: `git checkout -b feat/new-feature` → Work → `git push` → Pull Request → `develop` 머지.
    -   **배포**: `develop` 머지 시 운영 서버(`oracle-a1:/workspace/stock_monitoring`)에 **자동 배포**됨.
    -   **상세**: [배포 전략 문서](./deployment_strategy.md) 참조.

## 3. 디버깅 및 검증 전략 (Debugging & Validation Strategy)

### 3.1 통합 테스트 강제 (Integration Test Enforcement)
**배경**: `subscribe()` vs `psubscribe()` 실수처럼, 단위 테스트만으로는 실제 연결 문제를 발견 못 함.

**규칙**:
-   외부 의존성(Redis, DB, API)이 있는 컴포넌트는 **실제 연결 테스트 필수**.
-   "로그 정상" ≠ "데이터 흐름 정상". **실제 데이터 확인** 필수.

**체크리스트**:
1.  단위 테스트 (함수 로직만) ✅
2.  **통합 테스트** (실제 Redis/DB 연결) ✅ ⬅️ 필수
3.  **E2E 테스트** (전체 파이프라인) ✅ ⬅️ 배포 전 필수
### 3.1.5 에러 분석 게이트 (Error Analysis Gate - ZEVS)
**배경**: 동일한 에러가 다른 형태로 재발하는 것을 방지하기 위함.

**규칙**:
1. 모든 버그 수정 PR은 해당 이슈 문서의 `Failure Analysis` 섹션이 작성되어 있어야 한다.
2. 기발생 에러를 재현하는 **Regression Test**가 반드시 `tests/`에 포함되어야 하며, `test_registry.md`에 등록되어야 한다.
3. 이 과정이 생략된 PR은 품질 게이트(Gate 1~3) 통과 여부와 상관없이 반려할 수 있다.

---

### 3.2 Zero Data 알람 (Zero Data Alarm)
**규칙**: 데이터 수집 컴포넌트가 **5분 이상 0건 수집 → 즉시 디버깅 모드**.

**구현 예시**:
```python
if received_count == 0 and running_time > 300:  # 5분
    logger.error("🚨 ZERO DATA ALARM: No messages received!")
    logger.error(f"Redis URL: {redis_url}")
    logger.error(f"Subscribed channels: {pubsub.patterns}")
```

**의심 순서**: 연결 문제? → 구독 문제? → 필터링 문제?

### 3.3 API 문서 확인 (Library Documentation Check)
**규칙**: **처음 사용하는 라이브러리 메서드는 공식 문서 1회 필수 확인**.

**특히 주의**: Pub/Sub (`subscribe` vs `psubscribe`), WebSocket, 비동기 I/O

**실행 순서**: 공식 예제 → StackOverflow → **REPL 테스트** (5분 투자로 30분 절약)

### 3.4 TDD 완성도 등급 및 품질 게이트 (Quality Gate) [STRICT]
모든 모듈은 다음 품질 게이트를 통과해야 하며, 통과 시 **"보고서 형식"**으로 결과를 요약 제출한다.

#### 1단계: 유닛 테스트 (Unit - Logic)
- **통과 기준**: 핵심 파싱 로직 및 순수 함수 커버리지 100%.
- **제약**: 외부 I/O는 Mocking하되, `Pydantic` 스키마 검증은 생략하지 않음.
- **보고 필수항목**: 테스트 통과 건수, 예외 케이스 처리 여부.

#### 2단계: 통합 테스트 (Integration - Synergy)
- **통과 기준**: 실제 Redis/TimescaleDB 연결 하에 데이터 `Insert -> Select` 일관성 확인.
- **제약**: Docker 컨테이너 환경에서 수행 필수. 네트워크 지연 및 경합(Concurrency) 테스트 포함.
- **보고 필수항목**: DB 적재 건수, Redis 채널 구독 상태, 커넥션 풀 가용성.

#### 3단계: E2E 테스트 (Pipeline - Resilience)
- **통과 기준**: `수집기 -> Redis -> 아카이버 -> DB` 전 과정에서 데이터 유실율 0.01% 미만.
- **제약**: **Chaos Engineering** (프로세스 강제 종료 후 재시작) 시 데이터 복구 확인.
- **보고 필수항목**: 시스템 지연 시간(Latency), 복구 소요 시간(RTO), Zero-Data 알람 실효성.

## 4. 단일 진실 공급원 및 보고 의무 (SSoT & Reporting) [STRICT]
**규칙**: 모든 주요 변경(Feature 완성, 버그 수정)은 다음 **"품질 보고서(Quality Report)"**를 포함하여 3대 문서에 동시 반영한다.

1.  **[README.md](file:///home/ubuntu/workspace/stock_monitoring/README.md)**: 전체 시스템 가속도(Velocity) 및 Pillar 상태 업데이트.
2.  **[master_roadmap.md](file:///home/ubuntu/workspace/stock_monitoring/docs/strategies/master_roadmap.md)**: DoD 달성 여부 및 다음 단계 연결.
3.  **[test_registry.md](file:///home/ubuntu/workspace/stock_monitoring/docs/testing/test_registry.md)**: 품질 게이트(Tier 1~3) 통과 증명.
4.  **[Experiment Registry](file:///home/ubuntu/workspace/stock_monitoring/experiments/README.md)**: 모든 개별 실험 및 시뮬레이션 결과 영구 기록.
5.  **[Knowledge Base (INDEX)](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/knowledge_base.md)**: 세션 persistence 보장을 위한 기술 분석 및 의사결정 이력 허브.

**문서 동조화 프로토콜 (Sync Protocol)**:
- AI는 사용자가 `@.ai-rules.md`를 언급하거나 '문서 동기화'를 요청할 경우, 위 3대 문서를 **전수 Read**하여 상호 참조 링크와 태스크 상태가 일치하는지 Audit 수행 필수.
- 정합성 위배 발견 시 코딩 작업보다 **문서 동기화 수정을 최우선**으로 수행함.

**품질 보고서 필수 양식**:
```markdown
#### 📊 Quality Gate Report
- **Unit Gate**: [Pass/Fail] (커버리지 %, 주요 예외 처리 갯수)
- **Integration Gate**: [Pass/Fail] (DB 적재 성공율, Redis Pub/Sub 지연)
- **E2E Gate**: [Pass/Fail] (시나리오 완결성, Chaos 복구 시간)
- **SSoT Gate**: [Pass/Fail] (README/Roadmap/Registry 상호 동기화 여부)
```

**의무**: AI는 새로운 기능을 구현하거나 설계를 변경할 때, 위 세 문서의 정합성이 깨지지 않았는지 스스로 Audit하고 보고할 의무가 있다.
