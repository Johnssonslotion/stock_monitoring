# Issue-027: [SDLC] Smoke Test (test_smoke_modules.py) 구축

**Status**: Open  
**Priority**: P1  
**Type**: docs  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- 시스템 배포 또는 프리플라이트 체크 시 주요 모듈의 임포트 가능 여부 및 문법 오류를 자동으로 검증할 수 있는 스모크 테스트가 누락됨.
- 이로 인해 `recovery-worker`의 의존성 오류 등을 사전에 발견하지 못함.

## Acceptance Criteria
- [ ] `tests/test_smoke_modules.py` 작성: 모든 주요 Service(KIS, Kiwoom, Archiver) 및 유틸 모듈의 임포트 시도.
- [ ] 프리플라이트 체크(`scripts/preflight_check.py`)와 연동하여 장 시작 전 자동 실행.
