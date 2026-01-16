// Mock data for Order Book and Executions
export interface OrderBookLevel {
    price: number;
    volume: number;
}

export interface OrderBook {
    symbol: string;
    bids: OrderBookLevel[]; // 매수 호가 (5단계)
    asks: OrderBookLevel[]; // 매도 호가 (5단계)
    spread: number; // 스프레드 %
    timestamp: string;
}

export interface Execution {
    time: string;
    symbol: string;
    price: number;
    volume: number;
    type: 'BUY' | 'SELL';
    change: number; // 전거래 대비 %
}

// 삼성전자 목업 호가
export const MOCK_ORDERBOOK_SAMSUNG: OrderBook = {
    symbol: '005930',
    bids: [
        { price: 72100, volume: 15234 },
        { price: 72000, volume: 28451 },
        { price: 71900, volume: 35612 },
        { price: 71800, volume: 22334 },
        { price: 71700, volume: 18923 },
    ],
    asks: [
        { price: 72200, volume: 12456 },
        { price: 72300, volume: 19823 },
        { price: 72400, volume: 31245 },
        { price: 72500, volume: 25678 },
        { price: 72600, volume: 20134 },
    ],
    spread: 0.14, // (72200-72100)/72100 * 100
    timestamp: new Date().toISOString(),
};

// SK하이닉스 목업 호가
export const MOCK_ORDERBOOK_SKHYNIX: OrderBook = {
    symbol: '000660',
    bids: [
        { price: 142500, volume: 8234 },
        { price: 142000, volume: 12451 },
        { price: 141500, volume: 18612 },
        { price: 141000, volume: 9334 },
        { price: 140500, volume: 7923 },
    ],
    asks: [
        { price: 143000, volume: 9456 },
        { price: 143500, volume: 11823 },
        { price: 144000, volume: 15245 },
        { price: 144500, volume: 13678 },
        { price: 145000, volume: 10134 },
    ],
    spread: 0.35,
    timestamp: new Date().toISOString(),
};

// 목업 체결 내역 (삼성전자)
export const MOCK_EXECUTIONS_SAMSUNG: Execution[] = [
    { time: '15:29:58', symbol: '005930', price: 72150, volume: 523, type: 'BUY', change: 0.07 },
    { time: '15:29:56', symbol: '005930', price: 72100, volume: 1245, type: 'SELL', change: -0.07 },
    { time: '15:29:54', symbol: '005930', price: 72120, volume: 834, type: 'BUY', change: 0.03 },
    { time: '15:29:52', symbol: '005930', price: 72080, volume: 2134, type: 'SELL', change: -0.06 }, // 대량
    { time: '15:29:50', symbol: '005930', price: 72110, volume: 412, type: 'BUY', change: 0.04 },
    { time: '15:29:48', symbol: '005930', price: 72090, volume: 623, type: 'SELL', change: -0.03 },
];

// 목업 체결 내역 (SK하이닉스)
export const MOCK_EXECUTIONS_SKHYNIX: Execution[] = [
    { time: '15:29:59', symbol: '000660', price: 142800, volume: 312, type: 'BUY', change: 0.21 },
    { time: '15:29:57', symbol: '000660', price: 142500, volume: 845, type: 'SELL', change: -0.21 },
    { time: '15:29:55', symbol: '000660', price: 142650, volume: 534, type: 'BUY', change: 0.11 },
    { time: '15:29:53', symbol: '000660', price: 142400, volume: 1823, type: 'SELL', change: -0.18 }, // 대량
    { time: '15:29:51', symbol: '000660', price: 142600, volume: 287, type: 'BUY', change: 0.14 },
];

// 심볼별 데이터 매핑
export const ORDERBOOK_BY_SYMBOL: Record<string, OrderBook> = {
    '005930': MOCK_ORDERBOOK_SAMSUNG,
    '000660': MOCK_ORDERBOOK_SKHYNIX,
};

export const EXECUTIONS_BY_SYMBOL: Record<string, Execution[]> = {
    '005930': MOCK_EXECUTIONS_SAMSUNG,
    '000660': MOCK_EXECUTIONS_SKHYNIX,
};

// Generate Mock Candles
export const generateMockCandles = (count: number, startPrice: number, intervalSeconds: number = 86400) => {
    let price = startPrice;
    let time = Math.floor(Date.now() / 1000) - (count * intervalSeconds);
    const candles = [];

    for (let i = 0; i < count; i++) {
        const volatility = price * 0.002; // Reduced volatility for smoother ticks
        const change = (Math.random() - 0.5) * volatility;
        const close = price + change;
        const open = price;
        const high = Math.max(open, close) + Math.random() * volatility * 0.5;
        const low = Math.min(open, close) - Math.random() * volatility * 0.5;

        candles.push({
            time: time,
            open: +open.toFixed(0),
            high: +high.toFixed(0),
            low: +low.toFixed(0),
            close: +close.toFixed(0),
            volume: Math.floor(Math.random() * 10000)
        });

        price = close;
        time += intervalSeconds;
    }
    return candles;
};

export const MOCK_CANDLES = generateMockCandles(200, 72000, 86400); 
