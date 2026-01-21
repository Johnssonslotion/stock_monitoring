# Decision Record 004: Compliance Obligation as Separate Decision

- **Date**: 2026-01-17
- **Status**: Approved
- **Author**: Antigravity (User Request)

## 1. Context (배경)

현재 `.ai-rules.md`에 **AI 준수 의무**(AI Compliance Obligation) 내용이 포함되어 있습니다. 이 내용은 규칙 변경 프로토콜(Decision 4)과 혼합되어 있어 관리와 추적이 복잡해질 위험이 있습니다.

## 2. Decision (결정)

### 2.1 내용 분리
- **Compliance Obligation**을 별도의 Decision 4(004) 로 분리합니다.
- `.ai-rules.md`에서는 **Step 4**에 해당 Decision 004를 **참조**하도록 간단히 명시합니다.

### 2.2 관리 방안
- 모든 **Compliance** 관련 체크리스트는 Decision 004에 정의하고, `HISTORY.md`에 인덱스 항목을 추가합니다.
- 향후 규칙 변경 시, Decision 004를 **선행 조건**(Pre‑condition)으로 검토하도록 프로세스에 반영합니다.

## 3. Changes (변경 사항)

1. `docs/governance/decisions/004_compliance_obligation.md` 생성 (본 문서).
2. `.ai-rules.md` **Step 4**에 아래와 같이 링크 추가:
   ```markdown
   - **Step 4 – Rule Change Protocol** (준수 의무 포함) → [Decision‑004](004_compliance_obligation.md)
   ```
3. `docs/governance/HISTORY.md`에 새로운 인덱스 항목 추가 (버전 2.4).

## 4. Rationale (이유)

- **가시성**: Compliance 내용이 별도 문서에 있어 검토·수정이 용이.
- **추적성**: Decision 004가 히스토리와 연결돼 변경 이력이 명확.
- **자동 검증**: AI가 작업 전 `Decision‑004`를 읽고 체크리스트를 수행하도록 명시 가능.

## 5. Impact (영향)

- **Breaking**: 없음 – 기존 규칙은 동일하게 유지되며, 링크만 추가됩니다.
- **Risk**: 낮음 – 문서 업데이트만 수행.

---

*이 문서는 향후 Governance 프로세스에 따라 `HISTORY.md`에 인덱스가 추가될 예정이며, 모든 관련 팀은 해당 Decision을 참고해 준수 의무를 이행해야 합니다.*
