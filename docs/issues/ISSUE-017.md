# ISSUE-017: Implement DuckDBArchiver (Hybrid Architecture)

**Status**: Open
**Priority**: P1
**Type**: feature
**Created**: 2026-01-19
**Assignee**: Developer

## Problem Description
To achieve the **Hybrid DB Architecture** defined in [RFC-008](../governance/rfc/RFC-008-tick-completeness-qa.md), we need to implement `DuckDBArchiver`. This component will consume tick data from Redis and save it to a local DuckDB file in real-time batches, ensuring data persistence even if the main timeseries database fails.

## Acceptance Criteria
- [ ] **Real-time Consumption**: Subscribe to `market:ticks` Redis channel.
- [ ] **Batch Insert**: Buffer ticks and insert into DuckDB every 1 second (or 5,000 ticks).
- [ ] **Schema Compatibility**: Ensure `market_ticks` table schema matches the RFC definition (`execution_no` support).
- [ ] **Zero-Cost**: Must run with minimal memory footprint (unlike TimescaleDB).

## Technical Details
- **File**: `src/data_ingestion/archiver/duckdb_archiver.py`
- **DB Path**: `data/ticks.duckdb`
- **Library**: `duckdb`, `redis-py`

## Resolution Plan
1. Create `DuckDBArchiver` class.
2. Implement `_flush_buffer()` logic with `executemany`.
3. Register service in `docker-compose.yml` (or run as standalone process in `hybrid-service`).

## Related
- RFC: [RFC-008](../governance/rfc/RFC-008-tick-completeness-qa.md)
