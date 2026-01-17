# Decision Record 003: Relative Path for Internal Links

- **Date**: 2026-01-17T02:37
- **Status**: Approved
- **Author**: Antigravity (User Suggestion)

## 1. Context (배경)

현재 `.ai-rules.md`의 Governance Navigation 테이블에서 내부 문서 링크가 **절대 경로**로 되어 있습니다:
```markdown
file:///home/ubuntu/workspace/stock_monitoring/docs/governance/personas.md
```

**문제점**:
- 워크트리(`stock_backtest`)와 메인 저장소(`stock_monitoring`) 간 경로 불일치
- 다른 환경(로컬, 다른 개발자)에서 링크 깨짐
- 브랜치 간 이동 시 링크 무효화

## 2. Decision (결정)

### 2.1 링크 전략 변경
- **As-Is**: 절대 경로 (`file:///home/ubuntu/...`)
- **To-Be**: **프로젝트 루트 기준 명시적 상대 경로** (`./docs/governance/...`)
  - `./` 접두사로 프로젝트 루트임을 명확히 표시

### 2.2 적용 범위
- `.ai-rules.md` Section 1 (Governance Navigation)의 모든 링크
- Section 4 (Rule Change Protocol)의 `HISTORY.md` 링크

### 2.3 Rationale
- 워크트리/브랜치 독립성 확보
- 이식성(Portability) 향상
- IDE/마크다운 뷰어 호환성 개선
- **루트 기준임을 명시적으로 표현** (애매함 제거)

## 3. Changes

### Before
```markdown
[Personas & Council](file:///home/ubuntu/workspace/stock_monitoring/docs/governance/personas.md)
```

### After
```markdown
[Personas & Council](./docs/governance/personas.md)
```
**Note**: `./` 접두사로 프로젝트 루트 기준임을 명시

## 4. Impact
- **Breaking**: 없음 (상대 경로가 더 범용적)
- **Risk**: Low (단순 링크 수정)
