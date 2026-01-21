# Issue-024: [Bug] Recovery Worker 의존성(httpx) 누락 수정

**Status**: Open  
**Priority**: P2  
**Type**: bug  
**Created**: 2026-01-20  
**Assignee**: Developer

## Problem Description
- `recovery-worker` 컨테이너 실행 시 `httpx` 모듈을 찾지 못해 무한 재시작됨.

## Acceptance Criteria
- [ ] `pyproject.toml` 또는 Dockerfile에 `httpx` 의존성 명시적 추가.
- [ ] 컨테이너가 정상적으로 `Up` 상태를 유지하는지 확인.
