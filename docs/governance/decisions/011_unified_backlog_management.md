# ADR-011: Unified Backlog Management System

**Status**: 🟢 Approved  
**Date**: 2026-01-23  
**Author**: Council of Six  
**Deciders**: PM, Architect, Data Scientist, Infra, Developer, QA, Doc Specialist  
**Issues**: [Governance Simplification]

---

## 1. Context (배경)
프로젝트가 성장함에 따라 단기 작업을 관리하는 `BACKLOG.md`와 RFC 승인 후 이연된 작업을 관리하는 `deferred_work.md`로 정보가 파편화되었습니다. 이로 인해 다음과 같은 문제점이 발생하였습니다:
1.  **가시성 저해**: 이연된 작업들이 별도 문서에 격리되어 잊히거나 우선순위 검토에서 누락됨.
2.  **관리 비용**: 작업 상태 변경 시 두 문서를 동시에 업데이트해야 하는 번거로움.
3.  **복잡도**: 사용자와 AI가 프로젝트 전체 현황을 파악하기 위해 읽어야 할 문서가 늘어남.

## 2. Decision (결정)
"**Single Source of Truth (SSoT) for Tasks**" 원칙을 실현하기 위해 다음과 같이 결정합니다.

1.  **레지스트리 통합**: `deferred_work.md`를 폐지하고 모든 내용을 `BACKLOG.md`로 통합합니다.
2.  **백로그 구조 개편**: `BACKLOG.md`에 `## 4. Deferred Work (이연 작업)` 섹션을 신설하여 이연된 항목들을 관리합니다.
3.  **메타데이터 보존**: 통합 시 `Trigger`, `Priority`, `Related RFC/ISSUE` 정보를 반드시 유지합니다.
4.  **거버넌스 개정**: `.ai-rules.md`의 `7. Task Management` 섹션을 3-Tier에서 **2-Tier (Tactical Backlog + Strategic Roadmap)** 구조로 단순화합니다.

## 3. Rationale (근거)
- **정보 응집도 향상**: 모든 잠재적 작업이 하나의 백로그에서 관리되어 우선순위 조정이 용이해집니다.
- **워크플로우 단순화**: `/activate-deferred` 등의 명령이 단일 파일 내 섹션 이동으로 처리되어 DX(Developer Experience)가 향상됩니다.
- **거버넌스 전파력**: 관리해야 할 문서의 최소화를 통해 규칙 준수율을 높입니다.

## 4. Consequences (결과)
- **Positive**: 작업 추적성 강화, 관리 포인트 단일화, 문서 간 정합성 오류 제거.
- **Negative**: `BACKLOG.md` 파일의 크기가 커질 수 있음 (적절한 섹션 분리로 해결 가능).

---
**PM Final Approval**: ✅ Confirmed by Council of Six & Approved by User (2026-01-23)
