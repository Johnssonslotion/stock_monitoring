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
