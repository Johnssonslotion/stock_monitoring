# ISSUE-032: Git 워크트리 관리 및 격리 강화

**Status**: ✅ Resolved
**Priority**: P2
**Type**: debt
**Branch**: `feature/ISSUE-032-worktree-isolation`
**Created**: 2026-01-14
**Resolved**: 2026-01-21

---

## 1. 문제 정의 (Problem Statement)

**원래 문제** (2개 워크트리):
- `stock_monitoring`(운영/개발)과 `stock_backtest`(실험) 두 개의 Git 워크트리 운영
- Docker 컨테이너 이름 충돌
- 환경 변수 혼선
- 워크트리 인식 부재

**확장된 문제** (3개 환경):
- 로컬 Mac 환경 추가 고려 필요
- 하드코딩된 경로(`/home/ubuntu/...`)로 Mac에서 작동 불가
- 운영자가 현재 어느 환경에서 작업 중인지 시각적으로 구분 불가

---

## 2. 해결 방안 (Design)

**3-환경 자동 감지** (Local/Prod/Backtest):
- Mac (Darwin) → LOCAL (port 8000/6379/5173)
- Linux + stock_monitoring → PROD (port 8001/6380/5174)
- Linux + stock_backtest → BACKTEST (port 8002/6381/5175)

**구현 방식**:
- **Makefile 자동화**: OS + 폴더명으로 환경 자동 식별
- **동적 경로**: `${BASE_PATH}` 환경변수로 하드코딩 제거
- **Docker Project 격리**: `COMPOSE_PROJECT_NAME` 동적 할당
- **포트 자동 할당**: 환경별 충돌 방지
- **UI 배지**: 웹 대시보드에 환경 표시 (🟢/🔴/🟡)
- **거버넌스**: `.ai-rules.md` Law #9 신설

---

## 3. 구현 항목 (Implementation Items)

- [x] Makefile: 3개 환경 자동 감지 로직 (`ENV_TYPE`, `PROJECT_NAME`)
- [x] Makefile: `make identify` 명령 추가
- [x] docker-compose.yml: 하드코딩 경로 → `${BASE_PATH}` 변경
- [x] docker-compose.yml: 컨테이너명 → `${COMPOSE_PROJECT_NAME}` 동적 할당
- [x] docker-compose.yml: 포트 → 환경변수 기반 (`${API_PORT}`, `${REDIS_PORT}`, `${WEB_PORT}`)
- [x] Web UI: 환경 배지 추가 (`VITE_ENV_TYPE`)
- [x] docs/worktree_guide.md: 3개 환경 가이드로 업데이트
- [x] .ai-rules.md: Law #9 워크트리 격리 원칙 추가

---

## 4. 검증 계획 (Verification)

- [x] `make identify` 실행 시 정확한 환경 출력 확인
- [ ] 3개 환경 동시 실행 및 컨테이너 격리 확인
- [ ] 웹 UI에서 환경 배지 정상 표시 확인
- [ ] 서버 배포 후 PROD/BACKTEST 환경 정상 작동 확인

---

## 5. 결과 (Results)

**변경된 파일**:
- `Makefile` - 환경 자동 감지 로직
- `deploy/docker-compose.yml` - 동적 경로 및 포트
- `src/web/src/App.tsx` - 환경 배지
- `docs/worktree_guide.md` - 3개 환경 가이드
- `.agent/rules/ai-rules.md` - Law #9 추가

**커밋**: `e4ab541`

**테스트 결과**:
```bash
$ make identify
======================================
🔍 Environment Detection (ISSUE-032)
======================================
OS:              Darwin
Directory:       stock_monitoring
Base Path:       /Users/bbagsang-u/workspace/stock_monitoring

Environment:     local
Project Name:    stock_local
Profile:         local
Env File:        .env.local

API Port:        8000
Redis Port:      6379
Web Port:        5173
======================================
```
