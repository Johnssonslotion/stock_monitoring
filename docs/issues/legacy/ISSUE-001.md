# ISSUE-001: Virtual Investment Simulation Platform (Paper Trading)

**Status**: Open (Doc Synced)
**Priority**: P1
**Type**: feature
**Created**: 2026-01-17
**Assignee**: Developer, Data Scientist
**Related**: `docs/ideas/stock_backtest/ID-virtual-investment-platform.md`, `RF-004`

## Problem Description
To validate trading strategies realistically without risking real capital, we need a simulation environment that accounts for "market frictions" such as taxes, commissions, slippage, and interest. Simple backtesting on past data often leads to overfitting and unrealistic profit expectations.

## Acceptance Criteria
- [ ] **VirtualExchange Adapter**: Implement an adapter that mimics the real broker API interface.
- [ ] **Cost Model Engine**: Accurate calculation of KR/US taxes, broker commissions, and margin interest.
- [ ] **Execution Simulation**: Logic to simulate order filling based on orderbook snapshots (limit/market orders) with configurable slippage.
- [ ] **Database Schema**: Tables for `virtual_accounts`, `virtual_orders`, `virtual_positions` created.
- [ ] **Dashboard Integration**: View virtual account balance and PnL in the System Dashboard.

## Technical Details
- **Architecture**: Adapter Pattern (Strategy -> BrokerAdapter -> VirtualBroker).
- **Database**: PostgreSQL (TimescaleDB not strictly required for account data, but good for consistency).
- **Reference**: See `docs/governance/decisions/RFC-004_virtual_investment_platform.md` for detailed design.

## Resolution Plan
1. Define DB Schema and apply via migration.
2. Implement `VirtualExchange` class in `src/broker/virtual.py`.
3. Implement `CostCalculator` utility.
4. Update `StreamManager` to handle virtual updates.
