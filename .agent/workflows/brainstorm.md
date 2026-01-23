---
description: Brainstorm and evolve ideas into roadmap items or RFCs
---

# Workflow: Brainstorm (Ideation)

이 워크플로우는 모호한 아이디어를 구체화하여 로드맵에 반영하거나 RFC로 승격시키기 위한 **아이디어 인큐베이팅** 프로세스를 관리합니다.

## Trigger Conditions
- 새로운 전략 아이디어 발생
- 시스템 개선 제안
- 비정기적 브레인스토밍 세션 시작
- 사용자 명령: `/brainstorm` or "아이디어 기록해줘"

## Steps

### 0. Context Analysis (Pre-requisite)
**Action**: `docs/governance/HISTORY.md` 및 `docs/ideas/IDEA_BANK.md` 검토
- 과거에 유사한 아이디어가 있었는지, 거버넌스 원칙과 상충되는지 확인합니다.

### 1. Identify Idea
**Action**: 아이디어의 핵심 요약 및 카테고리 분류
- **Title**: [아이디어 명칭]
- **Category**: `Strategy` / `Infrastructure` / `UX` / `Data`
- **Source**: [Persona] or [User]

### 2. Register to Idea Bank
**Action**: `docs/ideas/[project_name]/` 디렉토리에 아이디어 문서 생성
- **Location**: `docs/ideas/[project_name]/ID-[short-title].md`
- **Template**:
  ```markdown
  # IDEA: [Title]
  **Status**: 💡 Seed (Idea) / 🌿 Sprouting (Drafting) / 🌳 Mature (Ready for RFC)
  **Priority**: [P0-P3]
  
  ## 1. 개요 (Abstract)
  - 어떤 문제를 해결하거나 어떤 기회를 포착하는가?
  
  ## 2. 가설 및 기대 효과 (Hypothesis & Impact)
  - [가설]
  - [기대 효과]
  
  ## 3. 구체화 세션 (Elaboration)
  - [6인 페르소나의 초기 의견 - 간단히]
  
  ## 4. 로드맵 연동 시나리오
  - 이 아이디어가 실현된다면 어느 Pillar에 포함될 것인가?
  ```

### 3. Persona Workshop (Recursive Call)
**Action**: 필요한 경우 `/council-review` 워크플로우의 '약식' 호출
- 아이디어의 기술적 실현 가능성 및 비즈니스 가치 검토

### 4. Promotion Rules (승격 규칙)
**Action**: 아이디어의 상태 변화 관리
- **Seed** → **Sprouting**: 구체적인 구현 방안이 논의되기 시작할 때
- **Sprouting** → **Mature**: 기술 검증(PoC)이 완료되거나 상세 설계 준비가 끝났을 때
- **Mature** → **RFC**: `/create-rfc` 워크플로우 호출 시점으로 연결

### 5. Roadmap & Hub Update
**Action**: 아이디어 문서 생성 시 즉시 인덱싱을 수행합니다.
1. `docs/ideas/IDEA_BANK.md`에 새 아이디어 링크를 추가합니다.
2. 아이디어가 'Mature' 상태가 되면 로드맵의 'Pillar' 또는 'Deferred' 섹션에 예비 항목으로 추가합니다. (`master_roadmap.md` 업데이트)

### 6. Quality Gate (DoD)
**Action**: 생성된 문서의 정합성을 최종 확인합니다.
- `/run-gap-analysis`를 실행하여 `IDEA_BANK.md`와 개별 문서 간의 링크 및 형식(Documentation Standard) 준수 여부를 검증합니다.

### 7. Notify User
- 생성된 아이디어 문서 링크 제공
- 다음 단계(Research/RFC) 제안

## Example Usage

**User says:**
- "/brainstorm"
- "새로운 모멘텀 전략 아이디어가 있어"
- "인프라 최적화 아이디어 기록해줘"

**AI will:**
1. 아이디어 핵심 내용 수집
2. `docs/ideas/[project]/`에 문서 생성
3. 페르소나 의견 추가
4. 로드맵 예비 항목 등록
5. 보고

## Integration
- Links to: `/create-rfc`, `/create-roadmap`
- Updates: `ideas/README.md`, `[project]_roadmap.md`
