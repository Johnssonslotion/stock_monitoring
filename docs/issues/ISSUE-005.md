# ISSUE-005: 가상 투자 시뮬레이션 플랫폼 (Virtual Investment Simulation Platform)

**Status**: Open  
**Priority**: P1 (High)  
**Type**: Epic Feature  
**Created**: 2026-01-17  
**Assignee**: Developer, Data Scientist  

## Problem Description
현재의 단순 백테스팅은 과거 데이터 기반 수익률만 계산하여 현실성이 부족합니다. 실제 거래 시 발생하는 세금, 수수료, 슬리피지, 이자 등의 **마켓 프릭션(Market Frictions)**을 고려하지 않아, 전략의 실제 성과를 과대평가하는 경향이 있습니다.

## Design (Architecture)

### Components
```
Strategy Engine
    ↓
BrokerAdapter (Interface)
    ↓
┌─────────────┬──────────────┐
VirtualBroker   RealBroker (KIS/Kiwoom)
```

**Adapter Pattern** 사용:
- Strategy는 BrokerAdapter 인터페이스만 의존
- VirtualBroker와 RealBroker가 동일한 인터페이스 구현
- 전략 코드 수정 없이 실거래/모의거래 전환 가능

### Database Schema
```sql
CREATE TABLE virtual_accounts (
    account_id UUID PRIMARY KEY,
    user_id VARCHAR,
    balance DECIMAL,
    created_at TIMESTAMPTZ
);

CREATE TABLE virtual_positions (
    position_id UUID PRIMARY KEY,
    account_id UUID REFERENCES virtual_accounts,
    symbol VARCHAR,
    quantity INTEGER,
    avg_price DECIMAL,
    unrealized_pnl DECIMAL
);

CREATE TABLE virtual_orders (
    order_id UUID PRIMARY KEY,
    account_id UUID,
    symbol VARCHAR,
    order_type VARCHAR, -- MARKET, LIMIT
    quantity INTEGER,
    price DECIMAL,
    status VARCHAR, -- PENDING, FILLED, CANCELLED
    filled_at TIMESTAMPTZ
);
```

## Implementation Checklist
- [ ] DB Schema 마이그레이션 (`src/db/migrations/`)
- [ ] VirtualExchange 클래스 구현 (`src/broker/virtual.py`)
- [ ] CostCalculator 유틸리티 (`src/broker/cost_calculator.py`)
- [ ] Dashboard Virtual Account UI (`src/web/src/components/VirtualAccount.tsx`)
- [ ] E2E 테스트 (Place Order → Fill → PnL)

## Acceptance Criteria
- [ ] 세금 계산 정확도 99%+ (KR/US 거래세, 양도소득세)
- [ ] 슬리피지 시뮬레이션 (설정 가능)
- [ ] 호가창 스냅샷 기반 체결 로직

## Related PRs
(To be added)
