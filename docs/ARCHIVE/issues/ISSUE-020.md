# ISSUE-020: Implement Dual Data Collection Strategy (100 Symbols)

**Status**: Resolved
**Priority**: P1 (High)
**Type**: Feature
**Created**: 2026-01-19
**Assignee**: Developer

## Problem Description
To enhance market monitoring and detect sector rotation, the user requires an expanded data collection strategy covering 100 symbols, optimized for KIS and Kiwoom capabilities.
The agreed strategy (40/60/100) requires:
- **KIS**: Core 40 Stocks (Tick Only)
- **Kiwoom**: Core 40 Stocks (Orderbook Only) + 60 Sector Rotation Stocks (Tick + Orderbook)

## Acceptance Criteria
- [x] `configs/kr_symbols.yaml` updated with the full list of 100 symbols (Core 40 + Sector 60).
- [x] KIS Collector configured to collect **Ticks Only** for the Core 40 list.
- [x] Kiwoom Collector configured to collect **Orderbooks** for Core 40 and **Tick+Orderbook** for Sector 60.
- [x] Total Kiwoom slot usage does not exceed 100 (99 Symbols used).
- [x] Data ingestion verified for new symbols.

## Technical Details
- **Config File**: `configs/kr_symbols.yaml`
- **Collectors**: `src/data_ingestion/price/kis_websocket.py`, `src/data_ingestion/price/kiwoom_websocket.py` (or Unified Manager)
- **Reference**: `docs/ideas/stock_monitoring/ID-top-40-dual-collection.md`

## Resolution Plan
1.  **Config**: Update `configs/kr_symbols.yaml` to clearly structure `core_40` and `sector_30` groups.
2.  **Logic**: Update `UnifiedWebSocketManager` or specific collector classes to parsing the new config structure and apply the split subscription logic.
3.  **Deploy**: Restart collectors.
