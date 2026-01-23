# IDEA: Docs Deep Cleanup & Hub Optimization
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1

## 1. 개요 (Abstract)
- **Problem**: 90개 이상의 Markdown 문서가 여러 폴더에 산재되어 있어, 필요한 정보를 찾는 데 시간이 오래 걸리고 관리가 어려움. 중복된 리포트와 예전 이슈 파일들이 노이즈를 발생시킴.
- **Opportunity**: 불필요한 문서를 과감히 아카이빙하고, 핵심 문서를 허브(`docs/README.md`) 중심으로 재배치하여 지식 베이스의 밀도를 높임.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- [가설] 문서 수를 40% 이상 감축(통폐합/아카이빙)하고 허브를 최적화하면, AI와 개발자의 컨텍스트 로딩 효율이 대폭 향상될 것이다.
- [기대 효과] SSoT 신뢰도 상승, 최신 스펙 파악 속도 개선.

## 3. 구체화 세션 (Elaboration)
### 3.1. 전수 조사 발견 사항
- `docs/governance/` 및 `docs/reports/` 내에 다수의 중복된 Gap Analysis 리포트 존재.
- `docs/ideas/` 하위에 30개 이상의 아이디어 파일이 파편화됨.
- `docs/testing/` 내에 다양한 네트워크/환경 가이드가 산재함.

### 3.2. 최적화 전략 (Consolidation Plan)
1.  **Report Archiving**: 모든 과거 Gap Analysis, UX Review, Incident Report를 `docs/ARCHIVE/reports/[YYYY]/`로 이동.
2.  **Idea Indexing**: 유사한 아이디어들을 그룹화하여 하나의 상세 문서로 통합하거나 `docs/ideas/IDEA_BANK.md`에 요약본으로 관리.
3.  **Testing Master**: `docs/testing/` 내의 여러 가이드를 `TESTING_MASTER_GUIDE.md`로 통합.
4.  **Legacy Issues**: `docs/issues/` 내 완료된 이슈들을 `docs/ARCHIVE/issues/`로 격리.

## 4. 로드맵 연동 시나리오
- **Pillar**: Infrastructure & Maintenance
- **Workflow**: `@/manage-docs`를 활용한 정기적인 정수 조사 및 정리 프로세스 정착.
