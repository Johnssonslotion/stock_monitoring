# Gap Analysis Report - 2026-01-19

## Missing Specs
- [ ] **ZEVS Implementation Detail**: `ID-error-screening-system.md` covers the vision, but a technical spec for the `lifespan` handler and Redis subscriber task management in `src/api/main.py` is absent from `docs/specs/`.
- [ ] **Test Dependency Mocking Strategy**: Stricter guidelines for mocking `docker` and `asyncpg` in test environments are implemented in code but not formally documented in `docs/governance/development.md`.

## Inconsistencies
- [x] **API Auth Header**: Code updated to `x-api-key`, but `api_specification.md` may still refer to `Authorization` or `secret`. (Verified: Code uses `x-api-key`).
- [x] **Virtual Trading Schema**: `test_virtual_api.py` includes automated table creation, ensuring consistency with `database_specification.md`.

## Governance Violations
- [None] All changes follow the Zero-Cost and Data-First principles.

## Recommendations
- **Spec Update**: Add a "Lifecycle Management" section to `api_specification.md` describing the `lifespan` handler and background subscribers.
- **Workflow Consolidation**: Integrate the manual test fixes (Docker mocking) into a reusable pytest plugin or a `conftest.py` guideline.
