# ISSUE-020: Implement Dual Data Collection Strategy (70 Symbols)

**Status**: Open
**Priority**: P1 (High)
**Type**: Feature
**Created**: 2026-01-19
**Assignee**: Developer

## Problem Description
To enhance market monitoring and detect sector rotation, the user requires an expanded data collection strategy covering 70 symbols, optimized for KIS and Kiwoom capabilities.
Current coverage is limited and lacks the "Sector Rotation" targets.
The agreed "Maximized Strategy" (Idea: ID-top-40-dual-collection) requires:
- **KIS**: Top 40 Stocks (Tick Only)
- **Kiwoom**: Top 40 Stocks (Orderbook Only) + 30 Sector Rotation Stocks (Tick + Orderbook)

## Acceptance Criteria
- [ ] `configs/kr_symbols.yaml` updated with the full list of 70 symbols (Core 40 + Sector 30).
- [ ] KIS Collector configured to collect **Ticks Only** for the Core 40 list.
- [ ] Kiwoom Collector configured to collect **Orderbooks** for Core 40 and **Tick+Orderbook** for Sector 30.
- [ ] Total Kiwoom slot usage does not exceed 100.
- [ ] Data ingestion verified for new symbols.

## Technical Details
- **Config File**: `configs/kr_symbols.yaml`
- **Collectors**: `src/data_ingestion/price/kis_websocket.py`, `src/data_ingestion/price/kiwoom_websocket.py` (or Unified Manager)
- **Reference**: `docs/ideas/stock_monitoring/ID-top-40-dual-collection.md`

## Resolution Plan
1.  **Config**: Update `configs/kr_symbols.yaml` to clearly structure `core_40` and `sector_30` groups.
2.  **Logic**: Update `UnifiedWebSocketManager` or specific collector classes to parsing the new config structure and apply the split subscription logic.
3.  **Deploy**: Restart collectors.
