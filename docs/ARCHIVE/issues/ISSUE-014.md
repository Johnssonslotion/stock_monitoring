# ISSUE-013: External Health Monitoring Dashboard (Standalone Bridge)

**Status**: In Progress  
**Priority**: P1  
**Type**: feature  
**Created**: 2026-01-19  
**Assignee**: Developer + Architect

## Problem Description
OCI A1(중앙 허브)의 상태를 외부 클라우드(GCP, Northflank) 및 Netlify 환경에서 독립적으로 모니터링할 수 있는 경량화된 통합 대시보드가 필요함. 메인 엔진 소스 코드 노출을 최소화하고 리소스를 아끼기 위해 별도 레포지토리(또는 서브모듈)로 분리 운영해야 함.

## Acceptance Criteria
- [ ] OCI A1의 `system_metrics` 테이블을 조회하는 초경량 FastAPI 구축. (api/main.py)
- [ ] Vite + React + Tailwind 기반의 프리미엄 다크 테마 UI 구현. (web/App.tsx)
- [ ] Netlify(Front) 및 Northflank(Backend) 배포를 위한 설정 파일 완비.
- [ ] X-API-KEY 및 CORS 등 보안 아키텍처 적용.
- [ ] 메인 프로젝트와 독립적으로 Git Push가 가능하도록 구조화.

## Technical Details
- **Architecture**: Master(A1 DB) - Consumer(Status API) - View(Netlify UI)
- **Repo Structure**: Standalone templates in `src/monitoring/external_status/`
- **Security**: Middleware for API Key verification and CORS domain filtering.

## Resolution Plan
1. [x] [Design] 구현 계획 및 거버넌스 검토.
2. [x] [Backend] FastAPI 기반 모니터링 전용 API 개발.
3. [x] [Frontend] Vite/React/Tailwind 기반 대시보드 UI 개발.
4. [x] [IaC] Dockerfile, netlify.toml 등 배포 설정 작성.
5. [ ] [Deploy] 사용자 서브모듈 초기화 및 외부 클라우드 배포 지원.

## Related
- [IDEA-006](../ideas/stock_backtest/ID-external-collector-migration.md)
- [Implementation Plan](../../home/ubuntu/.gemini/antigravity/brain/8dca0696-8d4c-49a0-8f6a-cd153c4e9b66/implementation_plan.md)
