---
description: Create and track issues with automatic branch creation and backlog integration
---

# Workflow: Create Issue

This workflow creates a tracked issue, generates a feature/fix branch, and integrates with the backlog system.

## Trigger Conditions
- Bug reported
- Feature request
- Technical debt identified
- User command: `/create-issue`

## Steps

### 1. Issue Information Gathering
**Ask user for:**
- **Title**: Brief description (e.g., "Fix WebSocket reconnection logic")
- **Type**: `bug` / `feature` / `refactor` / `docs`
- **Priority**: `P0` (Critical) / `P1` (High) / `P2` (Medium) / `P3` (Low)
- **Description**: Detailed explanation
- **Acceptance Criteria** (optional): How to verify fix

---

### 2. Generate Issue ID
**Action**: Auto-increment issue number
- Scan `BACKLOG.md` for existing issues
- **Numbering Reset (v2)**: Start from `ISSUE-001` (Ignore legacy issues in `docs/issues/legacy/`)
- Format: `ISSUE-[NUMBER]` (e.g., `ISSUE-001`)

---

### 3. **Phase 1: Doc Sync** (Documentation First)
**Action**: Create issue artifacts and sync ONLY documentation.

**3a. Create Issue Document**
- **Location**: `docs/issues/ISSUE-[NUMBER].md`
- **Template**: (Standard Issue Template)

**3b. Add to BACKLOG**
- **Action**: Insert into `BACKLOG.md` under appropriate section
- **Format**: `| **ISSUE-[NUMBER]**: [Title] | [Persona] | [Priority] | [ ] | (Doc synced) |`

**3c. Immediate Doc Push (Required)**
- **Policy**: `docs/**` and `BACKLOG.md` changes must be pushed to `develop` immediately to prevent numbering conflicts.
  ```bash
  git add docs/issues/ BACKLOG.md
  git commit -m "docs: register ISSUE-[NUMBER]"
  git push origin develop
  ```

> [!NOTE]
> At this stage, NO feature branch is created. The issue is registered, but code work hasn't started.

---

### 4. **Phase 2: Resolution Start** (Problem Solving)
**Trigger**: When actual work begins (User explicitly requests or "Start Work")
**Action**: Create Branch from `develop` and start coding.

```bash
git checkout develop
git pull origin develop
git checkout -b [type]/ISSUE-[NUMBER]-[kebab-case-title]
```

**Update BACKLOG**: Update the status to `[/]` and add `[Branch: type/ISSUE-XXX]` link.

---

### 5. Create Issue Document (Optional for P0/P1)
**Action**: For critical issues, create tracking document

**Location**: `docs/issues/ISSUE-[NUMBER].md`

**Template:**
```markdown
# ISSUE-[NUMBER]: [Title]

**Status**: Open / In Progress / Resolved  
**Priority**: [P0/P1/P2/P3]  
**Type**: [bug/feature/refactor]  
**Created**: [Date]  
**Assignee**: [Person/Persona]

## Problem Description
[Detailed problem statement]

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Technical Details
[Code pointers, stack traces, etc.]

## Resolution Plan
[How to fix]

## Related
- Branch: `[branch-name]`
- RFC: [if applicable]
```

---

### 6. Link to Deferred Work (if applicable)
**Condition**: If issue stems from deferred work
**Action**: Cross-reference in `docs/governance/deferred_work.md`

---

### 7. Notify User
**Success Message:**
```
✅ Issue created successfully!

Issue ID: ISSUE-[NUMBER]
Title: [Title]
Priority: [P0/P1/P2/P3]
Branch: [branch-name]
Status: Added to BACKLOG.md

Next Steps:
1. Work on branch: git checkout [branch-name]
2. When done: /merge-to-develop
```

---

## Example Usage

**User says:**
- "/create-issue"
- "버그 등록해줘"
- "새로운 이슈 만들어"

**AI will:**
1. Ask for title, type, priority
2. Generate ISSUE-042
3. Create branch: `bug/ISSUE-042-fix-reconnection`
4. Add to BACKLOG.md
5. Create issue doc (if P0/P1)
6. Notify user

---

## Integration

- **Links to**: `BACKLOG.md`, `/merge-to-develop`
- **Updates**: Task registry, deferred work (if applicable)
