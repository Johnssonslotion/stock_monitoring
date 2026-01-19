# RFC-006: Security & Governance Compliance
**Status**: 🏗️ Draft (Proposed)
**Date**: 2026-01-19
**Author**: Assistant
**Issues**: IDEA-002, IDEA-005

## 1. 개요 (Summary)
본 문서는 프로젝트의 보안 수준을 엔터프라이즈 급으로 격상하고, **단일 API Key** 환경에서의 운영 충돌을 물리적으로 방지하기 위한 거버넌스 및 기술적 제어 장치를 정의합니다.

## 2. 배경 (Motivation)
- **Secret Leak Risk**: 로컬 개발 및 진단 스크립트 작성 시 API Key가 코드에 하드코딩될 위험이 상존함.
- **Single-Key Conflict**: 오라클 인스턴스(Production)와 백테스트 엔진(Development)이 동일한 API Key를 공유할 경우, 중복 접속으로 인한 트레이딩 차단 위험이 있음.
- **Market Impact**: 장중(Market Hours)에 개발자의 우발적인 API 호출이 수집기의 안정성을 저해할 수 있음.

## 3. 제안 내용 (Proposal)

### 3.1. Secret Management (비밀 관리)
- **Environment Variable Enforcement**:
    - 모든 민감 정보(Key, Token)는 오직 `os.getenv()`를 통해서만 접근해야 함.
    - **Security Wrapper**: `src.core.security.SecurityManager` 클래스를 도입하여, 환경 변수가 아닌 방식으로 키에 접근하려는 시도를 감지 및 차단.
- **Pre-commit Hook**:
    - `detect-secrets` 또는 단순 Grep 기반 Hook을 도입하여 커밋 전 하드코딩된 Key 검사.

### 3.2. Single-Key Governance (단일 키 거버넌스)
수집기와 백테스트 엔진의 권한을 물리적으로 분리합니다.

| Component | Env File | KIS_APP_KEY | Role |
|:---:|:---:|:---:|:---:|
| **Collector** | `.env.prod` | `Exists` | **Producer**: Broker API 호출 및 데이터 저장 |
| **Engine** | `.env.backtest` | `Null` | **Consumer**: DB/Redis 조회만 가능 (API 호출 불가) |

- **Docker Compose Update**:
    - `real-collector`: `env_file: .env.prod`
    - `backtest-engine`: `env_file: .env.backtest`

### 3.3. MarketAwareGuard (장중 접근 제어)
개발자의 수동 진단 스크립트(`scripts/diagnostic_*.py`) 실행 시, 현재 시간이 **시장 운영 시간**이면 실행을 강제 차단합니다.

- **KR Block**: 08:30 ~ 16:00 (KST)
- **US Block**: 22:20 ~ 05:10 (KST, Summer) / 23:20 ~ 06:10 (KST, Winter)

## 4. 마이그레이션 계획 (Operations)

### 4.1. Server Migration (Deployment Workspace)
**대상**: 오라클 서버 `~/workspace/stock_monitoring`

1. **Environment Split**: 기존 `.env`를 복제하여 분리.
   ```bash
   cp .env .env.prod       # 기존 내용 유지 (수집기용)
   touch .env.backtest     # 빈 파일 생성 (백테스트용)
   ```
2. **Deploy**: 변경된 `docker-compose.yml` 배포.

### 4.2. Local Development (Optional)
로컬에서도 동일한 구조를 유지하기 위해 파일을 생성합니다. (Git에는 무시됨)
```bash
cp .env .env.prod
touch .env.backtest
```

## 5. 결론 (Conclusion)
이 RFC가 승인되면 시스템은 **"물리적 키 격리"**와 **"시간차 접근"**이라는 이중 안전장치를 갖추게 되며, 단일 키 환경에서도 안전한 무중단 운영이 가능해집니다.
