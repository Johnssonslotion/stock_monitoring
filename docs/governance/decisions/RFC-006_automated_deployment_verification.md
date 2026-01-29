# RFC-006: Automated Deployment Verification (Log-Level)

## 1. Context (배경)
현재 배포 프로세스(`make up-prod`)는 컨테이너 상태(`State=Running`)만 확인하며, 내부 애플리케이션의 초기화 오류(예: `NameError`, `ImportError`, `ConnectionRefused`)를 감지하지 못합니다.
이로 인해 배포 성공(`Exit Code 0`)으로 보고되었으나 실제 서비스는 불능 상태인 "Silent Failure"가 발생할 위험이 있습니다. (사례: ISSUE-047 Hotfix 상황)

## 2. Decision (결정)
배포 워크플로우에 **"Deep Log Verification"** 단계를 의무화합니다.

### 2.1 Log Verification Standard
- **범위**: 모든 컨테이너 (API, Worker, Collector)
- **방식**: 배포 직후 30초간의 로그를 스캔하여 **Critical Error Keywords** 감지.
- **키워드**: `Traceback`, `Error`, `Exception`, `Fail`, `Critical`, `Refused`
- **조치**: 키워드 발견 시 즉시 배포 중단(Rollback) 또는 운영자 알림 (`Rollback Strategy`는 추후 고도화).

### 2.2 New Workflow: `/deploy-production`
기존 수동 매뉴얼을 대체하는 Agentic Workflow를 신설합니다.
1. `git push` & Tag Check
2. `make up-prod`
3. **Log Inspector** (New Step): `docker logs` 기반 에러 패턴 매칭.
4. Health Check (HTTP/Redis ping)

## 3. Consequences (영향)
- **Positive**: "성공한 줄 알았는데 죽어있는" 사태 방지. 배포 신뢰도 99.9% 확보.
- **Negative**: 배포 시간 약 30~60초 증가 (로그 스캔 대기).
- **Compliance**: `development.md`의 Deployment Section 업데이트 필요.

## 4. Implementation Plan
1. `scripts/verify_deployment_logs.py` 스크립트 작성 (Log Scanning Logic).
2. `.agent/workflows/deploy-production.md` 신설.
3. `docs/governance/development.md` 업데이트.
