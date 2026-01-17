# ISSUE-002: Standardize Backlog Issue IDs

**Status**: Open
**Priority**: P1
**Type**: Refactor (Governance)
**Created**: 2026-01-17
**Assignee**: AI Assistant

## Problem Description
The `BACKLOG.md` currently uses a mix of ID formats (`TICKET-XXX` for backend specs) or lacks IDs. The `/create-issue` workflow mandates `ISSUE-XXX` format. This inconsistency makes it difficult to track tasks uniformly.

## Acceptance Criteria
- [ ] All `TICKET-XXX` items in `BACKLOG.md` are renamed to `ISSUE-XXX`.
- [ ] `ISSUE-001` (Chart Zoom) is properly listed.
- [ ] Numbering is sequential (002, 003, ... for existing items).

## Plan
1. Rename `TICKET-001` -> `ISSUE-002` (DB View)
2. Rename `TICKET-002` -> `ISSUE-003` (WebSocket)
3. Rename `TICKET-003` -> `ISSUE-004` (Data Gap)
4. Rename `TICKET-004` -> `ISSUE-005` (API Error)
5. Update `BACKLOG.md` content.

## Related
- Branch: `refactor/ISSUE-002-standardize-backlog`
