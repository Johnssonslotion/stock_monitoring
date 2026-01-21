# 🧪 Testing Master Guide

> [!IMPORTANT]
> **위계 (Hierarchy)**: 이 문서는 테스트 전략, 환경 설정, 도구 실행 절차를 관리하는 **Procedural SSoT**입니다. "어떻게 테스트하는가"를 정의하며, 데이터 소스인 **[Test Registry](test_registry.md)**와 상호 보완적으로 작동합니다.
> **관리 워크플로우**: 테스트 실행 및 생애주기 관리는 **[`/manage-tests`](../../.agent/workflows/manage-tests.md)**를 참조하십시오.

## 1. 테스트 전략 및 레지스트리
- 모든 테스트 케이스의 최신 상태는 **[Test Registry](test_registry.md)**에서 확인할 수 있습니다.
- **[Failure Mode Analysis (FMEA)](FAILURE_MODE_ANALYSIS.md)**: 시스템 잠재 실패 지점 및 복구 시나리오 분석.
- **[Backend Unit Test Strategy](backend_unit_test_strategy.md)**: 백엔드 모듈별 유닛 테스트 방침.

## 2. E2E 테스트 실행 가이드

### 환경 준비
1. **Docker 백엔드 시작**:
   ```bash
   docker compose -f deploy/docker-compose.yml up -d redis timescaledb api-server
   ```
2. **백엔드 헬스체크**: `curl http://localhost:8000/api/v1/health`
3. **프론트엔드 시작**: `cd src/web && VITE_API_TARGET=http://localhost:8000 npm run dev`

### 자동화 테스트 실행
```bash
npx playwright test tests/e2e/map-first-layout.spec.ts
```

## 3. 네트워크 및 인프라 진단
- **[Network Diagnosis](network_diagnosis.md)**: 외부 접속 및 통신 장애 진단.
- **[Port Forwarding Guide](port_forwarding_guide.md)**: 오라클 클라우드 및 로컬 환경 포트 설정.

## 4. UI 및 대시보드 검증 상태
- **[UI Test Report](UI_TEST_REPORT.md)**: 상세 UI 시나리오 및 통과 내역.
- **[Local UI Test Status](LOCAL_UI_TEST_STATUS.md)**: 로컬 개발 환경에서의 시각적 검증 상태.

## 5. 장애 및 복원력 테스트 (Chaos & Resilience)
- 시스템의 안정성을 검증하기 위해 **FMEA**에 정의된 시나리오별 카오스 테스트를 수행합니다.
- **주요 시나리오**:
    - DB/Redis 순단 시 자동 재연결 및 데이터 백필.
    - 웹소켓 구독 중복(`ALREADY_IN_SUBSCRIBE`) 강제 발생 후 복구 확인.
    - Sentinel을 통한 60초 무응답 시 자동 재시작 로직 검증.

## 5. 트러블슈팅 (Quick Fix)
- **ERR_CONNECTION_REFUSED**: Vite 서버 또는 Docker 컨테이너 실행 확인.
- **API Error**: Proxy 설정(`VITE_API_TARGET`) 및 백엔드 헬스체크 확인.
- **Page Loading**: 브라우저 콘솔 로그 및 무한 루프 가능성 점검.

---
> [!NOTE]
> 본 가이드는 지속적으로 업데이트되며, 새로운 테스트 시나리오 도입 시 관련 섹션을 보강하십시오.
