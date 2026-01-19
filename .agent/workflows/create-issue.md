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

### 1.5. **RFC Requirement Check (Constitution v2.8)**
**Action**: Automatically detect if this task requires RFC instead of direct ISSUE creation.

**Check the following criteria (ANY = RFC needed)**:
1. Will this modify **3+ files/components**?
2. Does this require **DB Schema changes**?
3. Will this add **new external dependencies** (libraries, APIs)?
4. Does this need **architecture pattern decisions** (Adapter, Strategy, etc.)?
5. Will this require **integration/E2E tests**?

**If YES to any** → **STOP** and notify user:
```
⚠️ This task requires RFC first.

Reason: [Matched criteria]
Recommended: Create RFC-XXX via /create-rfc workflow
After RFC approval → Split into multiple ISSUEs

Proceed anyway? (Not recommended)
```

**If NO to all** → Continue to Step 2 (Generate Issue ID)

---

### 2. Generate Issue ID
**Action**: Auto-increment issue number based on ISSUE_SUMMARY.md

**2a. Review ISSUE_SUMMARY.md**
- **Location**: `docs/issues/ISSUE_SUMMARY.md`
- **Purpose**: Single Source of Truth for all active issues
- **Check**: Read the file to identify the highest existing ISSUE-XXX number
- **Validation**: Ensure no gaps in numbering (e.g., if 001-015 exist, next is 016)

**2b. Calculate Next ID**
- Find max number from ISSUE_SUMMARY.md
- Increment by 1
- Format: `ISSUE-[NUMBER]` (zero-padded to 3 digits, e.g., `ISSUE-016`)

**2c. Verify No Conflicts**
- Check `docs/issues/ISSUE-[NUMBER].md` does NOT already exist
- If exists, skip to next number

---

### 3. **Phase 1: Doc Sync** (Documentation First)
**Action**: Create issue artifacts and sync ONLY documentation.

**3a. Create Issue Document**
- **Location**: `docs/issues/ISSUE-[NUMBER].md`
- **Template**: (Standard Issue Template)

**3b. Update ISSUE_SUMMARY.md**
- **Action**: Add new issue to the summary table
- **Format**: `| ISSUE-XXX | [Title] | [Priority] | Open | [Assignee] | docs/issues/ISSUE-XXX.md |`
- **Location**: Append to the table in `docs/issues/ISSUE_SUMMARY.md`

**3c. Add to BACKLOG**
- **Action**: Insert into `BACKLOG.md` under appropriate section
- **Format**: `| **ISSUE-[NUMBER]**: [Title] | [Persona] | [Priority] | [ ] | (Doc synced) |`

**3d. Immediate Doc Push (Required + Auto-Push)**
- **Policy**: `docs/**` and `BACKLOG.md` changes must be pushed to `develop` immediately to prevent numbering conflicts.
- **Auto-Execute**: AI should automatically stage, commit, and push these changes without user intervention.
  ```bash
  git add docs/issues/ BACKLOG.md
  git commit -m "docs: register ISSUE-[NUMBER] - [Title]"
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
