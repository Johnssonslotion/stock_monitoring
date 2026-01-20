# RFC-003: Configuration Management Standard

- **Status**: Accepted
- **Date**: 2026-01-17
- **Drivers**: Antigravity AI

## Context
프로젝트 내 설정값(Configuration) 관리에 대한 명확한 기준이 없어, 포트 번호, 타임아웃, 전략 파라미터 등이 환경변수(`.env`)와 코드 내 하드코딩, 혹은 YAML 파일로 혼재되어 사용되고 있습니다.

## Decision
설정의 성격에 따라 **환경변수(Environment Variables)**와 **구성 파일(Config Files)**로 이원화하여 관리합니다.

### 1. 환경변수 (.env)
- **대상**: **"인프라 종속 정보"** 및 **"보안 민감 정보"**
- **기준**: 컨테이너/서버가 변경될 때 바뀌어야 하는 값. 빌드 타임이 아닌 런타임에 주입되어야 하는 값.
- **예시**:
    - `KIS_APP_KEY`, `KIS_APP_SECRET` (Secret)
    - `REDIS_URL`, `DB_HOST` (Connection)
    - `VITE_API_PORT`, `SERVER_PORT` (Infrastructure)

### 2. 구성 파일 (*.yaml / *.json)
- **대상**: **"애플리케이션 동작 로직"** 및 **"알고리즘 파라미터"**
- **기준**: Git으로 버전 관리가 필요하며, 인프라와 무관하게 코드의 로직을 제어하는 값.
- **예시**:
    - `backtest_config.yaml` (기간, 종목, 수수료율)
    - `logging_config.json` (로그 포맷, 핸들러)
    - `strategy_params.yaml` (RSI 기간, 매수 임계값)

## Consequences
- **Frontend**: API Port는 배포 환경(로컬/Prod/Backtest)에 따라 달라지므로, 반드시 **Docker Compose Environment**를 통해 주입해야 함.
    - **Option A (Port Only)**: `VITE_API_PORT` (Default: 8000). Host는 `window.location.hostname` 사용.
    - **Option B (Full URL)**: `VITE_API_URL` (예: `ws://remote:8000/ws`). Cross-Origin 개발 시 유용.
- **Backtest**: 전략 파라미터는 실험의 재현성이 중요하므로 **Config 파일**로 관리해야 함.

---

## Implementation Standards (2026-01-20 Update)

### 1. Environment Variable Schema (`.env.schema.yaml`)
모든 환경 파일이 준수해야 하는 변수 목록을 정의:
- **required**: 필수 변수 (KIS/Kiwoom API 키, DB 자격증명 등)
- **optional**: 선택적 변수 (APP_ENV, KIWOOM_MOCK 등)
- **defaults**: 기본값 (URL, 포트 등)

### 2. Validation Script (`scripts/validate_env.py`)
컨테이너 시작 전 환경변수 완전성을 검증:
```bash
# Manual validation
python3 scripts/validate_env.py --env-file .env.dev

# Automatic validation via Makefile
make validate-env-dev
make validate-env-prod
```

**Validation Checks**:
- 필수 변수 존재 여부
- 빈 값 또는 플레이스홀더 감지 (예: `YOUR_KEY_HERE`)
- OS 환경변수 우선순위 고려

### 3. Environment Parity Enforcement
**원칙**: 로컬에서 테스트 성공 → 운영 배포 시 바로 동작
- `.env.dev`, `.env.prod`, `.env.test` 모두 동일한 변수 구조 유지
- 차이점은 **값(value)**만 (예: `DB_NAME=stock_dev` vs `DB_NAME=stock_prod`)
- `.env.template`을 모든 환경 파일의 베이스로 사용

### 4. Makefile Integration
```makefile
up-dev: validate-env-dev  # Development 환경 시작 전 자동 검증
up-prod: validate-env-prod  # Production 환경 시작 전 자동 검증
```

**Fail-Fast Principle**: 환경변수 누락 시 컨테이너 시작을 차단하여, 런타임 실패를 사전 방지.

### 5. Pre-commit Hook (Future Enhancement)
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-env
      name: Validate environment files
      entry: python3 scripts/validate_env.py --env-file
      language: python
```

---

## References
- **Implementation Plan**: `docs/governance/decisions/RFC-003_implementation.md`
- **Council Review**: [Implementation Plan - Council of Six Section](file:///home/ubuntu/.gemini/antigravity/brain/c28c0160-33b4-40ae-aa0c-28a3d8bfc166/implementation_plan.md#council-of-six---페르소나-협의)
- **Issue**: ISSUE-022 (Environment Variable Standardization)
