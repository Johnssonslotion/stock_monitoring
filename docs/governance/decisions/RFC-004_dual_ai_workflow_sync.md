# RFC-004: Dual AI Workflow Synchronization Strategy

**Status**: Proposed
**Author**: Claude Code
**Date**: 2026-01-17
**Constitution Version**: v2.7

---

## 1. 배경 (Context)

### 문제점
- **현재 상황**: `.agent/workflows/`는 Gemini Antigravity의 커스텀 컨벤션
- **Claude Code**: `.claude/commands/`를 slash commands로 사용
- **Constitution Law #6**: "워크플로우 슬래시 커멘드 준수" 명시
- **불일치**: 두 AI 간 워크플로우 실행 메커니즘이 다름

### 영향
- Gemini: 자연어 해석 → 워크플로우 문서 참조 (비결정적)
- Claude: 슬래시 명령어 → 즉시 실행 (결정적)
- Constitution 준수 어려움 (AI별 다른 동작)

---

## 2. 제안 내용 (Proposal)

### 하이브리드 아키텍처 (Dual AI Support)

```
.agent/workflows/          ← SSoT (Single Source of Truth)
├── create-issue.md        ← 원본 (Git 추적)
├── run-gap-analysis.md
└── ...

.claude/commands/          ← Claude Code 전용 (심링크)
├── create-issue.md -> ../../.agent/workflows/create-issue.md
├── run-gap-analysis.md -> ../../.agent/workflows/run-gap-analysis.md
└── ...

scripts/sync-workflows.sh  ← 자동 동기화 스크립트
```

### 핵심 원칙
1. **SSoT**: `.agent/workflows/`가 유일한 원본
2. **심링크**: `.claude/commands/`는 실행 가능한 링크
3. **자동화**: `sync-workflows.sh` 스크립트로 동기화
4. **투명성**: 두 AI 모두 동일한 워크플로우 문서 참조

---

## 3. 구현 사항 (Implementation)

### 3.1. 동기화 스크립트
- **위치**: `scripts/sync-workflows.sh`
- **기능**:
  - `.agent/workflows/*.md` → `.claude/commands/*.md` 심링크 생성
  - README.md 제외 (메타 문서)
  - 기존 심링크 정리 (stale links 방지)

### 3.2. 워크플로우 인벤토리 (11개)
1. `/create-issue` - ISSUE 등록 및 브랜치 생성
2. `/run-gap-analysis` - 코드-문서 정합성 검증
3. `/council-review` - 6인 페르소나 협의
4. `/create-rfc` - RFC 문서 생성
5. `/create-spec` - Spec 문서 작성
6. `/activate-deferred` - 이연 작업 활성화
7. `/create-roadmap` - 로드맵 생성
8. `/brainstorm` - 아이디어 인큐베이팅
9. `/amend-constitution` - 헌법 개정
10. `/hotfix` - 긴급 프로덕션 수정
11. `/merge-to-develop` - 품질 게이트 병합

---

## 4. Constitution 개정 제안 (Amendment)

### 4.1. Section 6 신설 - "Dual AI Workflow Support"

```markdown
## 6. Dual AI Workflow Support

### 6.1. 워크플로우 아키텍처
- **SSoT**: `.agent/workflows/` (원본, Git 추적)
- **Execution**:
  - **Gemini Antigravity**: 자연어 해석 → `.agent/workflows/` 참조
  - **Claude Code**: Slash commands → `.claude/commands/` (심링크)

### 6.2. 동기화 프로토콜
- **스크립트**: `scripts/sync-workflows.sh`
- **실행 시점**:
  1. 새 워크플로우 추가 시
  2. 워크플로우 수정 시
  3. `.claude/` 디렉토리 초기화 시
- **검증**: `ls -la .claude/commands/` 확인

### 6.3. AI별 사용법
#### Gemini Antigravity
- 자연어: "새로운 ISSUE 만들어줘"
- AI가 `.agent/workflows/create-issue.md` 참조

#### Claude Code
- Slash command: `/create-issue`
- `.claude/commands/create-issue.md` (심링크) 실행
```

### 4.2. Law #6 개정 (LLM Enforcement)

**현재**:
> "AI는 모든 주요 작업을 시작하기 전 해당하는 **워크플로우 슬래시 커멘드**가 존재하는지 확인하고 이를 준수해야 한다."

**개정안**:
> "AI는 모든 주요 작업을 시작하기 전 해당하는 **워크플로우**가 존재하는지 확인하고 이를 준수해야 한다.
> - **Gemini**: `.agent/workflows/` 문서 참조
> - **Claude Code**: `/slash-command` 실행 (`.claude/commands/` 심링크)"

---

## 5. 영향 분석 (Impact Analysis)

### 5.1. Data
- **변경 없음**: 기존 `.agent/workflows/` 유지
- **추가**: `.claude/commands/` 심링크 (Git 추적 가능)

### 5.2. Cost
- **Zero Cost**: 심링크는 파일 복사 없음
- **유지보수**: `sync-workflows.sh` 1회 실행만 필요

### 5.3. Risk
- **낮음**: 심링크 방식은 비파괴적
- **롤백**: `.claude/commands/` 삭제로 즉시 복구 가능
- **호환성**: Gemini는 기존 방식 그대로 사용

### 5.4. Benefits
- ✅ 두 AI 동시 지원 (Gemini + Claude)
- ✅ Constitution 준수 (Law #6)
- ✅ 결정적 실행 (Claude의 slash commands)
- ✅ 워크플로우 중복 제거 (SSoT 원칙)

---

## 6. 승인 요청 (Approval Request)

### 6.1. Council Review 필요 여부
- **아키텍처 변경**: ❌ (기존 유지 + 심링크 추가)
- **규칙 변경**: ✅ (Constitution Section 6 신설, Law #6 개정)
- **결론**: **Council Review 필요**

### 6.2. 승인 시 액션 아이템
1. [ ] Constitution 개정 (Section 6 추가, Law #6 수정)
2. [ ] `HISTORY.md`에 v2.8 기록
3. [ ] `scripts/sync-workflows.sh` 실행
4. [ ] `.gitignore` 확인 (`.claude/commands/` 추적 여부)
5. [ ] README.md에 Dual AI Support 명시
6. [ ] 문서 커밋 및 push

---

## 7. 참고 문서 (References)
- Constitution v2.7: `.agent/rules/ai-rules.md`
- Documentation Standard: `docs/governance/documentation_standard.md` Section 7
- Workflows README: `.agent/workflows/README.md`
- Claude Code Docs: https://code.claude.com/docs/en/slash-commands.md
