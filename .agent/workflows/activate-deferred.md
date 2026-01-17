---
description: Activate a deferred work item and move it to active backlog
---

# Workflow: Activate Deferred Work

This workflow activates a deferred work item from the registry and moves it to the active backlog.

## Steps

1. **Identify the Work Item**
   - User specifies the Deferred Work ID (e.g., `DEF-003-001`) or title
   - Locate the item in `docs/governance/deferred_work.md`

2. **Update Deferred Registry**
   - Change Status from `⏳ DEFERRED` to `🔄 ACTIVE`
   - Add "Activated" timestamp

3. **Add to BACKLOG.md**
   - Insert the work item into `BACKLOG.md` under "2. 대기 중 (Todo)" section
   - Include: Task name, Priority, Dependencies, and link to RFC

4. **Create Task.md**
   - If Implementation Plan exists, copy it to current `task.md`
   - Update task status to reflect active work

5. **Notify User**
   - Confirm activation
   - Show updated BACKLOG.md entry

## Example Usage

**User says:**
- "DEF-003-001 백로그로 넘겨줘"
- "Config 분리 작업 시작할게"
- "Activate DEF-003-001"

**AI will:**
1. Update `docs/governance/deferred_work.md` (Status → ACTIVE)
2. Add entry to `BACKLOG.md` (Todo section)
3. Copy Implementation Plan to task.md
4. Report completion
