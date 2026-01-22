# DB Schema Verification Report
**Date**: 2026-01-21
**Scope**: Migration SQL vs Archiver vs Collectors
**Status**: ⚠️ **CRITICAL ISSUES FOUND**

---

## Executive Summary

**Total Issues**: 3
- 🔴 **P0 (Critical)**: 2 issues
- 🟠 **P1 (High)**: 1 issue

---

## Detailed Findings

### 🔴 Issue #1: market_orderbook Schema Mismatch (P0)

**Component Affected**: Migration SQL vs TimescaleArchiver

**Migration (004_add_market_orderbook.sql)**:
```sql
CREATE TABLE market_orderbook (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    total_ask_qty DOUBLE PRECISION,
    total_bid_qty DOUBLE PRECISION,
    ask_prices DOUBLE PRECISION[],    -- ARRAY format
    ask_volumes DOUBLE PRECISION[],   -- ARRAY format
    bid_prices DOUBLE PRECISION[],    -- ARRAY format
    bid_volumes DOUBLE PRECISION[]    -- ARRAY format
);
```

**TimescaleArchiver (timescale_archiver.py:126-149)**:
```python
CREATE TABLE market_orderbook (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    source TEXT,
    ask_price1..10 DOUBLE PRECISION,  -- Individual columns
    ask_vol1..10 DOUBLE PRECISION,    -- Individual columns
    bid_price1..10 DOUBLE PRECISION,  -- Individual columns
    bid_vol1..10 DOUBLE PRECISION     -- Individual columns
);
```

**Impact**:
- Archiver creates 43 columns, Migration creates 8 columns
- Existing DB has ARRAY format, new inserts expect flat columns
- **INSERT will fail or create wrong schema**

**Root Cause**: Migration 004 was created but archiver was never updated

---

### 🔴 Issue #2: Missing Timestamp Fields in Collectors (P0)

**Component Affected**: KiwoomTickData, MarketData schemas

**Expected (Migration 003 + Archiver)**:
```python
- broker: TEXT
- broker_time: TIMESTAMPTZ
- received_time: TIMESTAMPTZ
- sequence_number: BIGINT
- source: TEXT
```

**Current KiwoomTickData Schema (kiwoom_re.py:5-15)**:
```python
class KiwoomTickData(BaseModel):
    symbol: str
    price: float
    volume: float
    change: float
    timestamp: datetime  # Only this timestamp field
    # ❌ Missing: broker, broker_time, received_time, sequence_number
```

**Current MarketData Schema (schema.py:31-38)**:
```python
class MarketData(BaseMessage):
    symbol: str
    source: str  # ✅ Has this
    price: float
    change: float
    volume: float
    timestamp: datetime  # Only this timestamp field
    # ❌ Missing: broker, broker_time, received_time, sequence_number
```

**Impact**:
- Archiver expects these fields (timescale_archiver.py:213-216)
- When missing, fields are NULL in DB
- Loss of critical debugging information (latency tracking, deduplication)

**Data Flow**:
```
Collector → Redis → Archiver → DB
Missing ✗   NULL ✗   NULL ✗   NULL ✓
```

---

### 🟠 Issue #3: source Field Inconsistency (P1)

**Component Affected**: market_ticks table

**Migration 003**: No `source` column defined
**Migration 000 baseline**: No `source` column
**Archiver init_db()**: Creates `source TEXT DEFAULT 'KIS'`
**Archiver ALTER**: Adds `source` column dynamically

**Status**: ✅ Works (via ALTER), but inconsistent
**Risk**: Low (backward compatible), but should be in official migration

---

## Verification Matrix

| Component | market_ticks Columns | market_orderbook Schema | Timestamp Fields |
|-----------|---------------------|------------------------|------------------|
| **Migration 000** | 5 cols (time, symbol, price, volume, change) | ❌ Not exists | ❌ None |
| **Migration 003** | +4 cols (broker, broker_time, received_time, seq) | Same as ticks | ✅ Added |
| **Migration 004** | N/A | ✅ ARRAY format (8 cols) | Same as 003 |
| **Archiver init_db()** | 10 cols (adds source) | ❌ Flat format (43 cols) | ✅ Correct |
| **Archiver INSERT** | Uses 10 cols | Uses 43 cols | ✅ Reads all fields |
| **KiwoomTickData** | Provides 5 cols | Provides 8 fields | ❌ Missing 4 |
| **MarketData** | Provides 6 cols (has source) | N/A | ❌ Missing 4 |

---

## Impact Analysis

### Current State
- **DB Created By**: Archiver init_db() (43-column orderbook)
- **Migration 004 State**: Not applied (would conflict)
- **Data Flow**: Partially working
  - ✅ Ticks: Insert succeeds (NULLs for missing fields)
  - ⚠️ Orderbook: Insert succeeds (wrong schema but working)
  - ❌ Timestamp tracking: Not working (all NULLs)

### Production Risk
- **Data Quality**: Medium (losing latency/dedup info)
- **Schema Drift**: High (migration vs reality mismatch)
- **Future Bugs**: High (schema confusion)

---

## Recommendations

### Priority 1: Fix market_orderbook Schema (P0)

**Option A: Update Migration 004 to match Archiver (Recommended)**
```sql
-- migrations/004_add_market_orderbook_v2.sql
CREATE TABLE market_orderbook (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    source TEXT,
    ask_price1 DOUBLE PRECISION, ask_vol1 DOUBLE PRECISION,
    ...  -- 40 more columns
    bid_price10 DOUBLE PRECISION, bid_vol10 DOUBLE PRECISION
);
```

**Option B: Update Archiver to use ARRAY format**
- More work, requires changing save_orderbook() logic
- Better storage efficiency
- Breaking change to existing data

**Decision**: Option A (less risky)

### Priority 2: Add Timestamp Fields to Collectors (P0)

**File**: `src/data_ingestion/price/schemas/kiwoom_re.py`
```python
class KiwoomTickData(BaseModel):
    # Existing fields...
    timestamp: datetime

    # Add these:
    broker: str = "KIWOOM"
    broker_time: Optional[datetime] = None
    received_time: datetime = Field(default_factory=datetime.now)
    sequence_number: Optional[int] = None
```

**File**: `src/core/schema.py`
```python
class MarketData(BaseMessage):
    # Existing fields...

    # Add these:
    broker: Optional[str] = None
    broker_time: Optional[datetime] = None
    received_time: datetime = Field(default_factory=datetime.now)
    sequence_number: Optional[int] = None
```

### Priority 3: Create Official Migration for source Column (P1)

```sql
-- migrations/005_add_source_column.sql
ALTER TABLE market_ticks ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'KIS';
ALTER TABLE market_orderbook ADD COLUMN IF NOT EXISTS source TEXT;
```

---

## Action Items

- [ ] **P0-1**: Update Migration 004 or create 004_v2
- [ ] **P0-2**: Add timestamp fields to KiwoomTickData
- [ ] **P0-3**: Add timestamp fields to MarketData
- [ ] **P0-4**: Test schema changes in local environment
- [ ] **P1**: Create Migration 005 for source column
- [ ] **P1**: Update Gap Analysis report with this finding
- [ ] **Documentation**: Update data_schema.md to reflect actual schema

---

## Files Requiring Changes

1. `migrations/004_add_market_orderbook.sql` - Rewrite or deprecate
2. `src/data_ingestion/price/schemas/kiwoom_re.py` - Add 4 fields
3. `src/core/schema.py` - Add 4 fields to MarketData
4. `migrations/005_add_source_column.sql` - Create new
5. `docs/specs/data_schema.md` - Update documentation

---

**Report Generated**: 2026-01-21 15:00 KST
**Verified By**: Claude Sonnet 4.5 (Automated Schema Audit)
