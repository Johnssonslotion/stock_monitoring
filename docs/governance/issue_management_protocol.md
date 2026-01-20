# Issue Management Protocol

**Effective Date**: 2026-01-19
**Status**: Active

## 1. Immutable Issue IDs
To prevent history corruption and context loss, the following rules apply strictly to Issue ID modifications:

### Rule 1.1: Never Reuse IDs
- Once an Issue ID (e.g., `ISSUE-003`) is assigned to a topic, it **MUST NOT** be repurposed for a different topic.
- If an issue is abandoned or invalid, mark its Status as `Closed - Won't Fix` or `Obsolete`. Do not recycle the number.

### Rule 1.3: Similarity Audit (ZEVS)
- Every `bug` type issue **MUST** undergo a similarity audit against `docs/issues/` before coding.
- The outcome of the audit must be recorded in the issue's `Failure Analysis` section.

## 2. Issue Lifecycle
- **Open**: Problem identified + **Similarity Audit Complete**.
- **In Progress**: Work has started + **Regression Test Case Defined**.
- **Resolved**: Work complete + **Regression Test Passed**.
- **Closed**: Verification successful.

## 3. Conflict Resolution
- If an ID conflict occurs (e.g., two branches use `ISSUE-004`), the newer/less-advanced branch **MUST** rename its issue file immediately to the next available ID.
- The original ID owner retains the number to preserve commit history context.
