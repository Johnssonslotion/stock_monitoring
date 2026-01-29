# Incident Report: HOTFIX-2026-01-29-verification-worker-crash

## ⚠️ Severity: Critical
- **Status**: Resolved
- **Impact**: `verification-worker` 컨테이너가 배포 직후 무한 재시작 루프에 빠짐. 실시간 검증 및 일일 배치 작업 중단.

## 📅 Timeline
- **2026-01-29 21:05 KST**: ISSUE-047 (통합 검증 워커) 배포 완료.
- **2026-01-29 21:06 KST**: `verification-worker` Crash 탐지 (`NameError: name 'scheduler' is not defined`).
- **2026-01-29 21:10 KST**: 1차 핫픽스 적용 (import 및 변수 선언 수정).
- **2026-01-29 21:15 KST**: 2차 문제 발견 (`task_type` 불일치로 인한 작업 미처리).
- **2026-01-29 22:00 KST**: 최종 핫픽스 완료 및 정상 가동 확인.

## 🔍 Root Cause Analysis
1. **NameError**: `run_verification_worker` 함수 내에서 `scheduler` 변수를 사용하기 전 초기화하는 코드가 누락되거나 잘못된 위치에 있었음. (병합 과정에서의 실수)
2. **Task Type Mismatch**: Producer는 `full_verification`을 생성했으나 Consumer는 `verify_db_integrity`를 기대함. (RFC-005 설계와 구현의 괴리)
3. **Hardcoded List**: 검증 대상이 5개 종목으로 하드코딩되어 있어 전체 시장 감시가 불가능했음.

## 🛠️ Resolution & Action Items
- **Immediate Fix**: 
    - `src/verification/worker.py` 내 `scheduler` 초기화 로직 복구.
    - `task_type`을 `verify_db_integrity`로 통일.
    - `kr_symbols.yaml` 기반 동적 종목 로딩 구현.
- **Prevention (RFC-006)**: 
    - 배포 직후 로그를 자동 스캔하여 `NameError`나 `ModuleNotFoundError`를 감지하는 `scripts/verify_deployment_logs.py` 도입.
    - `/deploy-production` 워크플로우에 로그 검증 단계 필수 포함.

## ✅ Verification
- `verification-worker` 무한 재시작 중단 확인.
- 99개 전 종목 일일 배치 작업 정상 처리 완료 (DB 확인).
