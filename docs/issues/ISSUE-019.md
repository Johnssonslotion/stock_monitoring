# ISSUE-019: API E2E Test Environment Fix

## 1. Problem Description
The End-to-End (E2E) test `tests/test_pillar3_e2e.py` fails at the API verification step with default local configuration.
- **Error**: `asyncpg.exceptions.InvalidCatalogNameError: database "stockval" does not exist` (or similar connection errors).
- **Cause**: The `TestClient` in `main.py` tries to connect to the database using environment variables that might mismatch the actual local Docker environment (e.g., `DB_HOST`, `DB_PORT`, `DB_NAME`).
- **Impact**: Cannot verify API endpoints in CI/CD or local test runs effectively, even if the actual service works in Docker.

## 2. Scope
- Fix `src/api/main.py` or test configuration (`conftest.py`) to correctly handle database connections during tests.
- Ensure `DB_PORT` is correctly cast to integer (already done in hotfix, but needs verification).
- Configure `conftest.py` to override `DB_HOST` or start a test DB container if needed.

## 3. Operations
1. Analyze `src/api/main.py` config loading.
2. Create/Update `tests/conftest.py` to properly mock or configure `db_pool` for `TestClient`.
3. Verify `tests/test_pillar3_e2e.py` passes fully.

## 4. Acceptance Criteria
- [ ] `poetry run pytest tests/test_pillar3_e2e.py` passes without database connection errors.
- [ ] API endpoints `/api/v1/ticks/{symbol}` return 200 OK in test environment.
