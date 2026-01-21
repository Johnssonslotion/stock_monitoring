# ISSUE-032: Git 워크트리 관리 및 격리 강화

## 1. 문제 정의 (Problem Statement)
현재 시스템은 `stock_monitoring`(운영/개발)과 `stock_backtest`(실험) 두 개의 Git 워크트리를 운영하고 있으나, 다음과 같은 한계점이 존재함:
- **Docker 컨테이너 이름 충돌**: 두 워크트리에서 동시에 `make up`을 실행할 경우 동일한 컨테이너 이름을 사용하려 하여 충돌 발생.
- **환경 변수 혼선**: 워크트리별로 서로 다른 `.env` 파일을 로드해야 함에도 불구하고 실수가 발생하기 쉬움.
- **워크트리 인식 부재**: 코드가 자신이 백테스트 환경인지 운영 환경인지 알지 못해 잘못된 데이터베이스에 접근할 위험이 있음.

## 2. 해결 방안 (Design)
- **Makefile 자동화**: `DIR_NAME` 및 `.git` 형태를 감지하여 워크트리 성격 자동 식별.
- **Docker Project 격리**: `COMPOSE_PROJECT_NAME`을 폴더명 기반으로 할당하여 컨테이너 네임스페이스 격리.
- **포트 충돌 방지**: 워크트리(Backtest) 환경인 경우 자동으로 8001, 6380 포트를 사용하도록 유도.
- **거버넌스 업데이트**: `.ai-rules.md`에 워크트리 격리 원칙(Law #9) 명시.

## 3. 구현 항목 (Implementation Items)
- [ ] Makefile: `PROJECT_NAME` 및 `WORKTREE_TYPE` 로직 추가
- [ ] Makefile: `make identify` 명령 추가
- [ ] docs/worktree_guide.md 최신화
- [ ] .ai-rules.md: Law #9 신설

## 4. 검증 계획 (Verification)
- 두 워크트리 동시 실행 및 컨테이너 격리 확인.
- `make identify`의 정확한 환경 출력 확인.
