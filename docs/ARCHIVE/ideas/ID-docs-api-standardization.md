# IDEA: Documentation Hub & API Normalization
**Status**: 🌿 Sprouting (Drafting)
**Priority**: P1

## 1. 개요 (Abstract)
- **Problem**: 90개 이상의 문서가 산발적으로 존재하며, KIS/Kiwoom 등 외부 API 스펙이 통일되지 않아 연동 시 혼선 발생.
- **Opportunity**: 문서 인덱싱을 통한 접근성 강화 및 데이터 모델링 표준화를 통한 코드 유연성 확보.

## 2. 가설 및 기대 효과 (Hypothesis & Impact)
- [가설] 문서 허브를 구축하고 API를 표준화하면, 새로운 AI 에이전트나 개발자가 투입되어도 컨텍스트 파악 시간이 50% 단축될 것이다.
- [기대 효과] 브로커 추가 시(예: 바이낸스, 업비트) 기존 로직 수정 최소화.

## 3. 구체화 세션 (Elaboration)
- **Architect**: Normalization 레이어를 `src/core/models/`에 배치하여 강제성 부여 제안.
- **Doc Specialist**: `docs/README.md`를 통해 문서 계층 구조 시각화 제안.

## 4. 로드맵 연동 시나리오
- **Pillar**: Infrastructure & Governance
- **Target**: Phase 8 Intelligence (Log Analysis) 이전에 데이터 및 문서 기초 체력 확보.
