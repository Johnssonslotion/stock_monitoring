-- Virtual Investment Platform Tables
-- Based on RFC-004

-- 1. Virtual Accounts (가상 계좌)
CREATE TABLE IF NOT EXISTS virtual_accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    balance DECIMAL(20, 2) DEFAULT 0.00,  -- 예수금
    currency VARCHAR(5) DEFAULT 'KRW',    -- KRW, USD
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Virtual Positions (보유 종목)
CREATE TABLE IF NOT EXISTS virtual_positions (
    account_id INT NOT NULL REFERENCES virtual_accounts(id),
    symbol VARCHAR(20) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    avg_price DECIMAL(20, 4) DEFAULT 0.0000, -- 평단가
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (account_id, symbol)
);

-- 3. Virtual Orders (주문 내역)
CREATE TABLE IF NOT EXISTS virtual_orders (
    order_id UUID PRIMARY KEY,
    account_id INT NOT NULL REFERENCES virtual_accounts(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    type VARCHAR(10) NOT NULL CHECK (type IN ('LIMIT', 'MARKET')),
    price DECIMAL(20, 4), -- 주문 가격 (시장가는 NULL 가능)
    quantity INT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, FILLED, REJECTED, CANCELLED
    
    -- Execution Details
    filled_price DECIMAL(20, 4), -- 실제 체결가 (슬리피지 포함)
    filled_quantity INT DEFAULT 0,
    fee DECIMAL(20, 4) DEFAULT 0.00, -- 수수료
    tax DECIMAL(20, 4) DEFAULT 0.00, -- 세금
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    executed_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX idx_virtual_orders_account ON virtual_orders(account_id);
CREATE INDEX idx_virtual_orders_status ON virtual_orders(status);
