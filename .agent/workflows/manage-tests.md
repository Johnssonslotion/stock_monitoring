---
description: Lifecycle management of test cases (Analysis -> Registration -> Verification)
---

# Workflow: Manage Tests

이 워크플로우는 테스트 케이스의 생성부터 분석, 등록, 검증에 이르는 전 생애주기를 관리하며, 관련 문서 간의 동기화를 보장합니다.

## Trigger Conditions
- 새로운 기능 개발 (`/create-issue` 시점)
- 장애 발생 후 재발 방지 대책 수립 (`FMEA` 분석 시점)
- 사용자 명령: `/manage-tests`
- 아이디어 구체화: `/brainstorm` 결과물 반영 시

## Steps

### 1. Identify & Analyze (Failure Mode Analysis)
**Action**: 장애 시나리오 또는 기능 요구사항으로부터 테스트 필요성 도출
- **Analysis (w/ `/brainstorm`)**: 
  - "왜 이 실패가 발생하는가?" (Root Cause)
  - "어떤 검증 로직이 필요한가?" (Test Logic)
- **Output**: 신규 실패 모드 정의 및 `FAILURE_MODE_ANALYSIS.md` 업데이트.

### 2. Register Test Case
**Action**: `docs/operations/testing/test_registry.md`에 테스트 케이스 등록
- **ID 생성**: 카테고리별 명명 규칙(KR-*, CH-*, E2E-* 등) 준수.
- **Mapping**: 실제 테스트 파일 경로 또는 Manual 검증 절차 명시.
- **Status**: 초기 상태는 `⏳ 예정` 또는 `🟡 진행중`으로 설정.

### 3. Implement & Execute
**Action**: 실제 테스트 코드 작성 및 실행
- `tests/` 디렉토리에 코드 작성.
- **Execution Guide**: `TESTING_MASTER_GUIDE.md`의 절차에 따라 테스트 수행.

### 4. Update Status & Sync
**Action**: 테스트 결과에 따라 문서 일제 동기화
1. **Registry Update**: `test_registry.md`의 상태를 `✅ Pass` 또는 `❌ Fail`로 업데이트.
2. **FMEA Linkage**: FMEA 문서의 'Countermeasures' 항목과 해당 테스트 ID 연결 확인.
3. **Guide Feedback**: 테스트 과정에서 발견된 환경 설정 이슈 등을 `TESTING_MASTER_GUIDE.md`에 반영.

### 5. Reporting
- **Notification**:
  ```
  🧪 Test Lifecycle Updated
  
  Test ID: [CH-BRO-03]
  Subject: KIS Auth Failure Simulation
  Status: ✅ Pass
  Documents Synced: Registry, FMEA, Master Guide
  ```

## Integration
- **Primary SSoT (Registry)**: 모든 데이터의 정합성 기준.
- **Procedural SSoT (Guide)**: 실행 방법의 기준.
- **Analysis SSoT (FMEA)**: "왜 하는가?"에 대한 논리적 근거.
