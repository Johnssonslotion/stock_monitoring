# Known Issues & Future Improvements

## Docker E2E Environment Issues (Pending)

### Issue 1: Redis Connection in Docker
**Status**: Identified, Not Fixed  
**Branch**: `test/e2e-validation`

**Problem**:
- `configs/base.yaml` has hardcoded `redis://localhost:6379`
- Docker containers need `redis://redis:6379` (Docker network hostname)
- Environment variable `REDIS_URL` is set in docker-compose but not used by config.py

**Solution**:
- Add environment variable override in `src/core/config.py`
- Prioritize `os.environ.get("REDIS_URL")` over YAML config

**Code Change Needed**:
```python
# in config.py load() method
if "REDIS_URL" in os.environ:
    config_dict.setdefault("data", {})["redis_url"] = os.environ["REDIS_URL"]
```

---

### Issue 2: DuckDB Concurrent Access
**Status**: Identified, Not Fixed

**Problem**:
- Multiple containers (TickArchiver, NewsCollector) try to open same DuckDB file
- DuckDB doesn't support multi-process write access
- Error: `Conflicting lock is held in PID 0`

**Solutions (Choose One)**:
1. **Separate DBs**: Each collector writes to its own DB file
   - `data/ticks.duckdb`, `data/news.duckdb`
   - Merge in analysis phase
2. **Queue Pattern**: Use single writer service
   - Collectors → Queue (Redis Streams?) → Single Archiver → DuckDB
3. **PostgreSQL**: Replace DuckDB with multi-user DB for Docker env
   - Keep DuckDB for local development

**Recommendation**: Solution #1 (simplest)

---

## Phase 1-2 Validation Decision

**PM Decision (2026-01-04)**:  
Docker E2E issues postponed. Phase 1-2 considered **COMPLETE** based on:

✅ Unit Tests: 8/8 Passed
- TickCollector: 3 passed
- TickArchiver: 2 passed  
- NewsCollector: 3 passed

✅ Code Quality:
- All implementations follow design specs
- Proper error handling and logging
- Korean docstrings as per AI rules

✅ Infrastructure:
- Dockerfile created
- docker-compose.yml defined
- Makefile commands ready

**Next Steps**:
- Proceed to Phase 3: Strategy & Experimentation
- OR: Fix Docker issues in dedicated sprint
- Reference branch: `test/e2e-validation` (preserved)
