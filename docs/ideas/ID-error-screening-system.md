# IDEA: Zero-Leak Error Verification System (ZEVS)
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P0
**Source**: User / Antigravity
**Category**: Strategy / Data / Quality

## 1. 개요 (Abstract)
이미 발생한 에러가 다시 재발하지 않도록, 모든 이슈(특히 Bug) 생성 시 과거 에러 이력을 스크리닝하고, 해당 에러를 재현하는 테스트 케이스를 등록하도록 강제하는 시스템입니다. 단순한 이슈 추적을 넘어, **에러 스크리닝 → 테스트 케이스 정의 → 리그레션 검증**의 폐쇄 루프(Closed-loop)를 시스템적으로 구축합니다.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- **가설**: 이슈 생성 시점에서 과거 유사 에러를 검색하고 이에 대응하는 테스트 케이스 작성을 의무화하면, 동일 유형 에러의 재발률을 90% 이상 낮출 수 있다.
- **기대 효과**:
  - 에러 필터링 과정의 시스템화 (FMEA-Lite 수준의 분석).
  - 테스트 케이스 누락 방지 (Specification-First 강조).
  - 품질 게이트 통과 시 리그레션 자동 검증 강화.

## 3. 구체화 세션 (Elaboration - Council Opinions)

### 👔 PM
> "이미 발생한 에러를 스크림하는 과정이 없었다는 점은 뼈아픈 실책입니다. `/create-issue` 시점에 'Similarity Audit' 단계를 추가하여 중복 작업을 막고 과거의 교훈을 즉시 반영하겠습니다."

### 🏛️ Architect
> "이슈 문서(ISSUE-XXX.md)의 템플릿에 'Failure Mode Analysis' 섹션을 추가하여, 왜 기존 테스트가 이를 잡지 못했는지 분석하게 해야 합니다. 이것이 시스템적인 에러 필터링의 시작입니다."

### 🧪 QA Engineer
> "단순히 '테스트 완료'가 아니라, '어떤 테스트 ID가 이 버그를 잡는가'를 명시해야 합니다. `test_registry.md`와 이슈 문서 간의 양방향 링크(Bi-directional Linking)를 강제하겠습니다."

## 4. 워크플로우 통합 지점 (Integration Points)

### A. `/create-issue` 고도화 (스크리닝 단계 삽입)
- **Step 1.7: Error Similarity Search (Mandatory)**
  - 신규 보고된 에러 키워드로 `docs/issues/` 및 `docs/governance/reviews/` 검색.
  - 유사 사례 발견 시 "유사 이슈 발견: ISSUE-XXX. 당시 조치된 테스트 케이스([test_id])를 확인했습니까?" 알림.

### B. `ISSUE-XXX.md` 템플릿 수정 (분석 및 검증 강화)
- **Failure Analysis**: 왜 기존 테스트 게이트를 통과했는가?
- **Regression Test ID**: 이 에러를 재현/방지하기 위해 `test_registry.md`에 추가될 테스트 ID.

### C. `/merge-to-develop` 품질 게이트 강화
- **Verification Check**: PR 본문에 `Regression Test ID`가 포함되어 있고, 해당 테스트가 통과되었는지 자동 확인.

## 5. 에러 필터링 프로세스 (Systematic Error Filtering)

1. **식별 (Identification)**: 에러 발생 시 로그/현상 수집.
2. **대조 (Consistency Check)**: 과거 유사 에러 존재 여부 확인. (Similarity Audit)
3. **분석 (FMEA-Lite)**: 발생 원인, 치명도, 기존 테스트의 한계 분석.
4. **정의 (Prescription)**: 반영될 테스트 케이스(Case/ID) 확정.
5. **봉인 (Sealing)**: 테스트 통과 및 로드맵/레지스트리 업데이트.

## 6. 로드맵 연동 시나리오
- `master_roadmap.md`의 **Pillar 4: Quality & Governance Automation**에 포함.
- 2026-01-20 주간의 핵심 인프라 작업으로 설정.
