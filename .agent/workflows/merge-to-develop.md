---
description: Automate develop branch merge with quality gates and gap analysis
---

# Workflow: Merge to Develop

This workflow automates the merge process to the `develop` branch with built-in quality gates, automatic gap analysis, and conditional council review.

## Trigger Conditions
- Pull Request to `develop`
- User command: `/merge-to-develop`
- Feature branch ready for integration

## Steps

### 1. Pre-Merge Validation
**Action**: Verify merge readiness
- Check current branch (must not be `develop`)
- Verify no uncommitted changes: `git status --porcelain`
- Confirm `develop` is up-to-date: `git fetch origin develop`

**Block Conditions**:
- If on `develop` → Error: "Cannot merge from develop to develop"
- If uncommitted changes → Error: "Commit or stash changes first"

---

### 2. Run Test Suite
**Action**: Execute all tests
pytest tests/ --cov --cov-report=term
```
(User requested: `poetry run pytest tests/` - adjusted dynamically)
```bash
poetry run pytest tests/
```

**Pass Criteria**:
- All tests pass
- Coverage ≥ 80% (if applicable)

**Block Conditions**:
- If tests fail → Block merge, notify user with error details

---

### 3. **Auto-Trigger: Gap Analysis** (Recursive Call)
**Action**: Execute `/run-gap-analysis` workflow

**Purpose**: Ensure code-documentation alignment before merge

**Process**:
1. Read workflow: `.agent/workflows/run-gap-analysis.md`
2. Execute all steps from that workflow
3. Generate: `docs/governance/gap_analysis_report_[YYYY-MM-DD].md`

**Block Conditions**:
- If **P0 issues** found → Block merge
- Notify user: "Critical gap detected. Fix before merging."

**Warning Conditions**:
- If P1 issues found → Warn user, allow merge with acknowledgment

---

### 4. Check Modified Files
**Action**: Analyze what files changed
```bash
git diff --name-only develop..HEAD
```

**Smart Analysis**:
- If `src/core/` or `src/api/` changed → Flag as "Architecture Change"
- If `docs/governance/decisions/RFC-*.md` modified → Mark as "RFC Approved"
- If `src/` files changed without corresponding spec update → Warning

**Output**: List of changed categories

---

### 5. Conditional Council Review (Recursive Call)
**Trigger Conditions** (from personas.md):
- Architecture changes (2+ components affected)
- API schema breaking changes
- Modified core modules (`src/core/`, `src/api/`)

**Action**: If triggered, execute `/council-review` workflow

**Process**:
1. Read workflow: `.agent/workflows/council-review.md`
2. Conduct 6 persona deliberation
3. Record in `implementation_plan.md`
4. Get PM final decision

**Block Conditions**:
- If PM vetoes → Block merge
- If Council requires changes → Block merge

**Skip Conditions**:
- Only documentation changes
- Only test file changes
- RFC already approved for this work

---

### 6. Update BACKLOG
**Action**: Mark completed tasks
- Scan commit messages for task IDs
- Update `BACKLOG.md` (move from "In-Progress" to "Done")

**Optional**: Link to completed RFC/Spec documents

---

### 7. Execute Merge
**Action**: Perform the actual merge
```bash
git checkout develop
git merge [source-branch] --no-ff -m "Merge: [branch-name] - [summary]"
```

**Merge Message Format**:
```
Merge: feat/new-feature - Added Config Management System

- Implemented RFC-003
- Gap Analysis: PASS
- Council Review: APPROVED (if applicable)
- Tests: PASS (Coverage: 85%)
```

---

### 8. Post-Merge Actions

#### 8.1 Create Tag
```bash
git tag develop-$(date +%Y%m%d-%H%M)
git push origin develop --tags
```

#### 8.2 Update Documentation
- Add entry to `docs/governance/HISTORY.md` (if RFC involved)
- Update `master_roadmap.md` (mark phase/task complete)

#### 8.3 Cleanup Source Branch (Optional)
**Ask user**: "Delete source branch `[branch-name]`? (y/n)"
- If yes: `git branch -d [branch-name]`
  
---

### 9. Notify User
**Success Message**:
```
✅ Merge to develop completed successfully!

Summary:
- Branch: [source-branch]
- Tests: ✅ PASS
- Gap Analysis: ✅ PASS (Report: docs/governance/gap_analysis_report_[date].md)
- Council Review: [✅ APPROVED / ⏭️ SKIPPED]
- Tag: develop-[timestamp]
- Commits merged: [N]
```

**Failure Message** (if any gate failed):
```
❌ Merge blocked

Reason: [Specific failure]
Action Required: [What user needs to do]
```

---

## Integration with Other Workflows

### Workflow Call Graph
```
/merge-to-develop
├─> /run-gap-analysis (ALWAYS)
│   └─ Generate gap report
└─> /council-review (CONDITIONAL)
    └─ If architecture changes
```

### Return Handling
- `/run-gap-analysis` returns: P0/P1 issues count
- `/council-review` returns: APPROVED / VETOED

---

## Safety Features

### 1. No Infinite Recursion
- Max recursion depth: 2 (main → sub-workflow only)
- Sub-workflows (gap-analysis, council-review) do NOT call other workflows

### 2. Rollback on Failure
- If merge succeeds but post-merge fails → Tag not created (safe)
- If tests fail → No merge attempted

### 3. Audit Trail
- All actions logged
- Gap report saved permanently
- Council deliberation recorded (if triggered)

---

## Example Usage

**User says:**
- "/merge-to-develop"
- "develop에 머지해줘"
- "Ready to merge to develop"

**AI will:**
1. Validate current state
2. Run tests
3. **Auto-execute** `/run-gap-analysis`
4. Check for architecture changes
5. **Conditionally execute** `/council-review`
6. Perform merge
7. Tag and update docs
8. Notify user with summary
