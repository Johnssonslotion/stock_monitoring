---
description: Create and manage project roadmap with auto-generated structure
---

# Workflow: Create Roadmap

This workflow creates a comprehensive project roadmap and automatically generates supporting documents and directory structure.

## Trigger Conditions
- New project initialization
- Major system redesign
- Quarterly planning
- User requests new roadmap

## Steps

### 1. Gather Requirements
   - Project name/title
   - Strategic pillars (e.g., Pillar 0: Governance, Pillar 1: Infrastructure)
   - Timeline estimate (Q1, Q2, etc.)
   - Key milestones

### 2. Create Roadmap Document
   - Location: `docs/strategies/[project_name]_roadmap.md`
   - Include sections:
     - **Overview**: Project vision and goals
     - **Quality Gates**: Pass criteria for each pillar
     - **Strategic Pillars**: Detailed breakdown
       - Goal
       - Phases (with Done/In-Progress/Deferred status)
     - **Timeline**: Quarterly estimates
     - **Council Approval**: Final remarks from personas

### 3. Auto-Generate Directory Structure
   Create supporting directories:
   ```
   docs/
   ├── strategies/[project_name]_roadmap.md          # 로드맵 문서
   ├── ideas/[project_name]/                         # 아이디어 인큐베이터 (신규)
   ├── specs/[project_name]/                         # Feature specs
   ├── phases/[project_name]/                        # Phase별 상세 문서
   │   ├── phase_0_governance/
   │   │   ├── tasks.md
   │   │   └── checklist.md
   │   ├── phase_1_infrastructure/
   │   └── phase_2_data_pipeline/
   └── reports/[project_name]/         # Progress reports
   ```

### 4. Generate Phase Templates
   For each phase, create:
   - **`tasks.md`**: Checklist of deliverables
   - **`spec_index.md`**: Links to related specs
   - **`test_strategy.md`**: Quality gate definitions

### 5. Create Tracking Documents
   - `docs/ideas/[project_name]/README.md` - 아이디어 뱅크 인덱스
   - `docs/reports/[project_name]/progress_tracker.md` - 주간 진행 상황
   - `BACKLOG.md` entry for Phase 0 (if not exists)

### 6. Link to Master Documents
   - Update `master_roadmap.md` (if global roadmap exists)
   - Add reference in `README.md` under "Roadmap" section

### 7. Notify User
   - Show created roadmap path
   - List auto-generated directories
   - Prompt for first phase activation

## Example Usage

**User says:**
- "/create-roadmap"
- "새로운 프로젝트 로드맵 만들어줘"
- "백테스팅 시스템 로드맵 생성"

**AI will:**
1. Ask for project name, pillars, timeline
2. Create `docs/strategies/backtest_roadmap.md`
3. Generate directory structure:
   - `docs/specs/backtest/`
   - `docs/phases/backtest/phase_0_governance/`
4. Create phase templates (tasks.md, spec_index.md)
5. Update BACKLOG.md with Phase 0 entry
6. Notify user with summary

## Auto-Generated Files Example

When creating "Backtest System" roadmap:

```
docs/
├── strategies/
│   └── backtest_roadmap.md              [CREATED]
├── specs/backtest/
│   └── README.md                         [CREATED]
├── phases/backtest/
│   ├── phase_0_governance/
│   │   ├── tasks.md                      [CREATED]
│   │   ├── spec_index.md                 [CREATED]
│   │   └── test_strategy.md              [CREATED]
│   └── phase_1_infrastructure/
│       └── ...
└── reports/backtest/
    └── progress_tracker.md               [CREATED]
```

## Template: Phase tasks.md

```markdown
# Phase X: [Name] - Task Checklist

## Objectives
- [Objective 1]
- [Objective 2]

## Deliverables
- [ ] [Deliverable 1]
- [ ] [Deliverable 2]

## Quality Gate
- [ ] Unit tests pass
- [ ] Spec documents updated
- [ ] Council review completed
```

## Integration
- Links to: `/create-spec`, `/create-rfc`
- Updates: `BACKLOG.md`, `master_roadmap.md`
