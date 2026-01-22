# ADR-010: Governance Sync Gate (No Review, No Work)

**Status**: 🟢 Approved  
**Date**: 2026-01-22  
**Author**: Council of Six  
**Deciders**: PM, Architect, Data Scientist, Infra, Developer, QA  
**Issues**: [v2.17 Constitution Amendment]

---

## 1. Context (배경)
AI가 수많은 작업 컨텍스트 속에서 과거에 확립된 거버넌스 규칙(특히 `development.md`의 상세 배포 수칙이나 `ground_truth_policy.md`의 참값 우선순위)을 잊거나 무시하여 코드와 정책 간의 괴리가 발생하는 현상이 관찰되었습니다. 이를 방지하기 위해 작업 시작 전 강제적인 지식 동기화(Knowledge Sync) 절차가 필요합니다.

## 2. Decision (결정)
"**No Review, No Work**" 원칙을 실효성 있게 강제하기 위해 다음 조치를 확정합니다.

1.  **헌법 5조 0항 신설**: 작업 전 거버넌스 문서를 전수 Read했는지 확인하는 검증 게이트를 0순위로 추가합니다.
2.  **검토 문서 명시 의무**: AI는 응답 상단에 현재 작업을 위해 검토한 거버넌스 문서 목록을 반드시 출력해야 합니다.
3.  **대상 문서**: `development.md`, `ground_truth_policy.md`, `infrastructure.md` 등 작업 성격에 맞는 핵심 거버넌스 문서를 포함합니다.

## 3. Rationale (근거)
- **전방향 방어**: 구현 시작 전 규칙을 재확인함으로써 사후 수정 비용을 획기적으로 절감합니다.
- **컨텍스트 최신화**: AI의 Short-term memory에 핵심 규정들을 다시 로드하여 정합성 있는 의사결정을 유도합니다.
- **책임성 강화**: 무엇을 읽었는지 명시하게 함으로써 사용자에게 프로세스 투명성을 제공합니다.

## 4. Consequences (결과)
- **Positive**: 거버넌스 준수율 비약적 향상, 환경 오설정(Port, ENV) 및 정책 위반(Truth Policy) 감소.
- **Negative**: 작업 착수 시 미미한 지연 발생 (문서 Read 단계). 

---
**PM Final Approval**: ✅ Confirmed by Council of Six (2026-01-22)
