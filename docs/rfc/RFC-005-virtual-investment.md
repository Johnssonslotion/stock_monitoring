# RFC-005: 가상 투자 시뮬레이션 플랫폼 (Virtual Investment Simulation Platform)

**Status**: Proposed  
**Priority**: P1  
**Author**: System Architect  
**Date**: 2026-01-17  
**Related**: `docs/ideas/stock_backtest/ID-virtual-investment-platform.md`

## 1. 배경 (Context)

현재의 단순 백테스팅은 과거 데이터를 기반으로 수익률만 계산하여 현실성이 부족합니다. 실제 거래 시 발생하는 세금, 수수료, 슬리피지, 이자 등의 **마켓 프릭션(Market Frictions)**을 고려하지 않아, 전략의 실제 성과를 과대평가하는 경향이 있습니다.

## 2. 제안 내용 (Proposal)

### 2.1 아키텍처 (Architecture)

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

### 2.2 주요 컴포넌트

1. **VirtualExchange** (`src/broker/virtual.py`)
   - `place_order(symbol, quantity, price, order_type)` 구현
   - 호가창 스냅샷 기반 체결 시뮬레이션
   - 슬리피지 모델 적용 (설정 가능)

2. **CostCalculator** (`src/broker/cost_calculator.py`)
   - KR/US 세금 계산 (거래세, 양도소득세)
   - 브로커 수수료 (증권사별 차등)
   - 마진 이자 (신용거래 시)

3. **Database Schema**
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

4. **Dashboard Integration**
   - System Tab에 "Virtual Account" 섹션 추가
   - 잔고, 포지션, PnL 실시간 표시

## 3. 영향 분석 (Impact Analysis)

### 3.1 Data
- **Migration 필요**: 새로운 3개 테이블 생성
- **기존 데이터 영향**: 없음 (독립적 스키마)

### 3.2 Cost
- **Zero Cost 준수**: PostgreSQL 사용 (기존 인프라)
- **추가 리소스**: 없음

### 3.3 Risk
- **복잡도 증가**: 4개 이상 컴포넌트 추가
- **테스트 부담**: E2E 테스트 필요 (주문 → 체결 → PnL 계산)

## 4. 구현 계획 (Implementation Plan)

승인 시 다음 ISSUE로 분해:
1. **ISSUE-013**: DB Schema 마이그레이션
2. **ISSUE-014**: VirtualExchange 클래스 구현
3. **ISSUE-015**: CostCalculator 유틸리티
4. **ISSUE-017**: Dashboard Virtual Account UI
5. **ISSUE-018**: E2E 테스트 (Place Order → Fill → PnL)

## 5. 참고 (References)
- QuantConnect 가상거래 구조
- Backtrader Broker Simulation
