# Governance Protocol Enforceability Analysis

## 사용자의 질문
> "거버넌스가 이게 명확한가? ai-rules를 호출하면 위의 맥락을 다 준수할까?"

## 1. Current State (현재 상황)

### 강점 ✅
1. **명확한 절차**: Rule Change Protocol이 단계별로 정의됨
2. **History Separation**: 헌법과 프로젝트 히스토리가 분리됨
3. **Spec Verification Gate**: 검증 항목이 나열됨

### 약점 ⚠️
1. **선언적(Declarative)이지 강제적(Imperative)이 아님**
   - "AI는 ~해야 한다"는 요구사항일 뿐, 실제 강제 메커니즘 없음
   - 예: "HISTORY.md를 먼저 읽어라" → AI가 안 읽으면?

2. **검증 실패 시 Action이 모호함**
   - "즉시 작업 중단 → 사용자에게 보고"라고 되어있지만
   - AI가 스스로 "검증 실패"를 판단할 수 있나?

3. **맥락 의존성**
   - `.ai-rules.md`는 매 요청마다 컨텍스트에 포함되지만
   - AI가 매번 이를 "숙지"하고 "적용"한다는 보장 없음

## 2. 문제의 본질

### AI의 한계
- LLM은 "지시를 읽는다" ≠ "지시를 반드시 따른다"
- 특히 복잡한 절차적 요구사항("먼저 A를 하고, 그 다음 B를...")은 누락되기 쉬움
- 사용자 요청이 급하면 절차를 건너뛸 가능성

### 현재 프로토콜의 Gap
```
[현재]
"AI는 HISTORY.md를 읽어야 한다"

[문제]
- 언제 읽어야 하나? (매번? 특정 상황에만?)
- 안 읽으면 어떻게 되나?
- 누가 확인하나?
```

## 3. 개선 방안 (Recommendations)

### 3.1 즉시 적용 가능 (Quick Wins)
1. **체크리스트를 `.ai-rules.md` 최상단에 배치**
   ```markdown
   ## 🚨 AI 작업 전 필수 확인사항 (Pre-Flight Checklist)
   매 세션 시작 시 반드시 확인:
   - [ ] HISTORY.md 최신 3개 항목 검토 완료
   - [ ] 요청 작업이 Roadmap에 존재하는가?
   - [ ] 관련 Spec 문서가 존재하는가?
   ```

2. **Section 순서 재배치**
   - 헌법(Laws) → **절차(Protocol) → 검증(Verification)**
   - 중요한 것을 위로

3. **AI Duty를 각 Section 상단에 중복 명시**
   - "LLM Enforcement"를 별도 Law로만 두지 말고
   - 모든 주요 Section 상단에 "AI는 이 섹션을 적용할 때 반드시..."

### 3.2 중기 개선 (Medium Term)
1. **규칙 준수 여부를 사용자가 확인할 수 있는 Artifact 도입**
   - 예: `governance_checklist.md`를 매 세션마다 갱신
   - AI가 "HISTORY 읽음 ✅", "Spec 확인 완료 ✅" 기록

2. **Workflow Diagram 추가**
   - 텍스트만으로는 부족
   - Mermaid Flowchart로 "사용자 요청 → Decision → Spec → Code" 흐름 시각화

3. **Decision Template 제공**
   - `docs/governance/decisions/TEMPLATE.md` 생성
   - AI가 Decision 작성 시 이 템플릿을 강제로 참조하도록

### 3.3 근본적 해결 (Long Term)
1. **Pre-Commit Hook 도입**
   - `.ai-rules.md` 변경 시 자동으로 HISTORY.md가 업데이트되었는지 검증
   - Git Hook으로 물리적 강제

2. **AI에게 "자기 평가" 요구**
   - 작업 완료 후 "이 작업이 거버넌스를 준수했는가?" 체크리스트 제출
   - `session_review.md`에 기록

## 4. 현실적 제안 (Pragmatic Approach)

### "완벽한 자동화"는 불가능
- AI가 100% 규칙을 따르게 만들 수는 없음
- **대신 "사용자 확인 비용"을 최소화**

### Hybrid Model
1. **Critical Path는 강제 확인**
   - Rule Change (헌법 수정) → 반드시 Decision 문서 요구
   - 문서 없으면 AI가 작업 거부

2. **Non-Critical은 권장사항**
   - 일반 코딩 → Spec 있으면 좋지만 없어도 진행 가능
   - 단, 사후에 Gap Analysis로 보완

3. **사용자가 "심판"**
   - AI는 "나는 이렇게 했습니다" 보고
   - 사용자가 최종 승인/거부

## 5. 즉시 조치사항

### `.ai-rules.md`에 추가할 섹션 (최상단)
```markdown
---
## 🔴 AI 준수 의무 (AI Compliance Obligation)

본 규칙은 **강제 사항(Mandatory)**입니다. AI는 다음을 준수해야 합니다:
1. **매 세션 시작 시**: `HISTORY.md`를 읽고 최근 3개 변경사항 파악
2. **코드 작성 전**: 해당 기능의 Spec 존재 여부 확인
3. **헌법 수정 시**: 반드시 Decision Document 작성 후 진행
4. **불확실할 때**: 작업 중단 후 사용자에게 명시적으로 질의

**준수 실패 시**: 사용자는 해당 세션의 모든 작업을 거부할 권리가 있습니다.
---
```

## 6. 결론

**Q: 현재 거버넌스가 명확한가?**
- A: 절차는 명확하나, **강제력이 약함**

**Q: AI가 이를 준수할까?**
- A: **100% 보장 불가**. 하지만 다음으로 개선 가능:
  1. 체크리스트를 최상단 배치
  2. AI에게 명시적으로 "준수 의무" 선언
  3. 사용자가 확인할 수 있는 기록 남기기

**추천**: 위 "즉시 조치사항"을 `.ai-rules.md`에 추가하고, 사용자가 매 세션마다 간단히 확인
