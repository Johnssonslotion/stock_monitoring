# Issue Management Protocol

**Effective Date**: 2026-01-19
**Status**: Active

## 1. Immutable Issue IDs
To prevent history corruption and context loss, the following rules apply strictly to Issue ID modifications:

### Rule 1.1: Never Reuse IDs
- Once an Issue ID (e.g., `ISSUE-003`) is assigned to a topic, it **MUST NOT** be repurposed for a different topic.
- If an issue is abandoned or invalid, mark its Status as `Closed - Won't Fix` or `Obsolete`. Do not recycle the number.

### Rule 1.2: Check Before Create
- Before creating a new issue, the Assignee (AI/User) **MUST** list existing files in `docs/issues/` to identify the next available sequence number.
- **Protocol**: `ls docs/issues/ | grep ISSUE-`

## 2. Issue Lifecycle
- **Open**: Problem identified.
- **In Progress**: Work has started.
- **Resolved**: Work complete, awaiting verification.
- **Closed**: Verification successful.

## 3. Conflict Resolution
- If an ID conflict occurs (e.g., two branches use `ISSUE-004`), the newer/less-advanced branch **MUST** rename its issue file immediately to the next available ID.
- The original ID owner retains the number to preserve commit history context.
