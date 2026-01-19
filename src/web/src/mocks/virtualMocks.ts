// Mock data for Virtual Investment Platform
export interface VirtualAccount {
    account_id: number;
    name: string;
    balance: number;
    currency: string;
    created_at: string;
    updated_at: string;
}

export interface VirtualPosition {
    symbol: string;
    quantity: number;
    avg_price: number;
    current_price: number;
    unrealized_pnl: number;
    unrealized_pnl_pct: number;
}

export interface VirtualOrder {
    order_id: string;
    symbol: string;
    side: 'BUY' | 'SELL';
    type: 'LIMIT' | 'MARKET';
    price: number | null;
    quantity: number;
    status: 'PENDING' | 'FILLED' | 'CANCELLED' | 'REJECTED';
    filled_price: number | null;
    filled_quantity: number;
    fee: number;
    tax: number;
    created_at: string;
    executed_at: string | null;
}

export const MOCK_VIRTUAL_ACCOUNT: VirtualAccount = {
    account_id: 1,
    name: "Virtual Account 01",
    balance: 100000000.00,
    currency: "KRW",
    created_at: "2026-01-17T00:00:00Z",
    updated_at: "2026-01-17T08:00:00Z"
};

export const MOCK_VIRTUAL_POSITIONS: VirtualPosition[] = [
    {
        symbol: "005930",
        quantity: 10,
        avg_price: 70000.00,
        current_price: 72000.00,
        unrealized_pnl: 20000.00,
        unrealized_pnl_pct: 2.86
    },
    {
        symbol: "000660",
        quantity: 5,
        avg_price: 140000.00,
        current_price: 142500.00,
        unrealized_pnl: 12500.00,
        unrealized_pnl_pct: 1.79
    }
];

export const MOCK_VIRTUAL_ORDERS: VirtualOrder[] = [
    {
        order_id: "550e8400-e29b-41d4-a716-446655440000",
        symbol: "005930",
        side: "BUY",
        type: "LIMIT",
        price: 70000.00,
        quantity: 10,
        status: "FILLED",
        filled_price: 70000.00,
        filled_quantity: 10,
        fee: 105.00,
        tax: 0.00,
        created_at: "2026-01-17T07:59:00Z",
        executed_at: "2026-01-17T08:00:00Z"
    }
];

export const MOCK_VIRTUAL_PNL = {
    realized_pnl: 50000.00,
    unrealized_pnl: 32500.00,
    total_pnl: 82500.00,
    total_pnl_pct: 0.08,
    total_trades: 5,
    win_rate: 0.6,
    period_start: "2026-01-17T00:00:00Z",
    period_end: "2026-01-17T08:00:00Z"
};
