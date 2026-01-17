# ISSUE-006: API Error Handling & Logging

**Status**: Open
**Priority**: P2 (Medium)
**Type**: Reliability
**Created**: 2026-01-17
**Assignee**: Backend Engineer

## Problem Description
Current API error handling is generic. We need structured error codes for the client and detailed stack traces in logs for debugging 500 errors.

## Acceptance Criteria
- [ ] Enhanced logging for 500 errors (include stack trace).
- [ ] Define client-facing error codes (e.g., `DB_CONNECTION_ERROR`, `INVALID_SYMBOL`).

## Technical Details
- **Framework**: FastAPI (Exception Handlers)
- **Logging**: Python `logging` module with JSON formatter optional.
