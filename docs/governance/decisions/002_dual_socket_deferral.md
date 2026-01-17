# Decision Record 002: Dual Socket Deferral (Governance Refinement)

- **Date**: 2026-01-17T02:33
- **Status**: Approved (Priority Shift)
- **Author**: Antigravity (on behalf of User)
- **Related**: Decision-001 (Superseded)

## 1. Context (배경)

Decision-001에서 Dual Socket 전략을 승인했으나, 사용자 피드백에 따라 **"기능보다 프로세스가 우선"**이라는 원칙이 확립되었습니다.
현재 시점에서는 Governance Protocol 자체를 완성하는 것이 Dual Socket 구현보다 중요합니다.

## 2. Decision (결정)

### 2.1 헌법 롤백
- **Immutable Law #2 (Socket Strategy)**: "Dual Socket 허용" → **"Single Socket 강제"**로 복구.
- **Rationale**: 현재는 검증된 Single Socket 아키텍처를 유지하고, Dual Socket은 Governance가 안정된 후 재검토.

### 2.2 Implementation Deferral
- Dual Socket 구현을 **BACKLOG**로 이동.
- 향후 `master_roadmap.md`의 Pillar 2에서 "Future Phase"로 재진입 가능.

### 2.3 History Preservation
- Decision-001의 논의 내용은 삭제하지 않고 보존.
- Status를 "Approved" → "Deferred (Pending Governance Completion)"로 변경.

## 3. Governance Protocol Completeness Check

### 현재 수립된 프로토콜:
1. ✅ Rule Change Process (RFC → Council → History → Amendment)
2. ✅ History Separation (Constitution vs Project)
3. ✅ Schema Strictness (Swagger/OpenAPI)
4. ✅ Roadmap-Driven Cascade
5. ⚠️ **부족한 부분**:
   - Spec Verification 체크리스트의 구체화
   - AI의 자동 검증 로직 (어떤 조건에서 작업을 중단할지)
   - 변경 승인 기준 (어떤 것은 Auto-Proceed, 어떤 것은 User Review)

### 보완 필요 항목:
- `.ai-rules.md`에 "Spec Verification Gate" 섹션 추가 필요
- Auto-Proceed vs Manual Review 기준 명확화

## 4. Next Actions
1. `.ai-rules.md` Law #2 복구 (Single Socket)
2. `HISTORY.md`에 이 결정 추가
3. Governance Protocol 보완 후 `master_roadmap.md` 업데이트
