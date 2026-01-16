// src/web/src/mocks/marketMocks.ts

export const MOCK_SECTORS = [
    {
        name: '반도체 (Semiconductor)',
        avgChange: 1.45,
        etf: { symbol: '091160', name: 'KODEX 반도체', change: 1.2, price: 34000 },
        children: [
            { symbol: '005930', name: '삼성전자', change: 1.5, marketCap: 450000000000000 },
            { symbol: '000660', name: 'SK하이닉스', change: 2.1, marketCap: 95000000000000 },
        ]
    },
    {
        name: '이차전지 (Battery)',
        avgChange: -1.2,
        etf: { symbol: '305720', name: 'KODEX 2차전지산업', change: -1.1, price: 22000 },
        children: [
            { symbol: '373220', name: 'LG에너지솔루션', change: 0.25, marketCap: 90000000000000 },
            { symbol: '207940', name: '삼성바이오로직스', change: -0.58, marketCap: 70000000000000 },
            { symbol: '006400', name: '삼성SDI', change: -2.1, marketCap: 30000000000000 },
        ]
    },
    {
        name: '자동차 (Auto)',
        avgChange: -0.5,
        etf: { symbol: '091180', name: 'KODEX 자동차', change: -0.4, price: 18500 },
        children: [
            { symbol: '005380', name: '현대차', change: -0.74, marketCap: 50000000000000 },
            { symbol: '000270', name: '기아', change: 3.16, marketCap: 45000000000000 },
            { symbol: '012330', name: '현대모비스', change: -2.55, marketCap: 25000000000000 },
        ]
    }
];

export const MOCK_NEWS = [
    {
        id: '1',
        time: '2026-01-15T10:30:00Z',
        symbol: '005930',
        title: '삼성전자, 차세대 AI 반도체 수주 성공',
        sentiment: 'POSITIVE',
        impact: 0.85,
    },
    {
        id: '2',
        time: '2026-01-15T14:20:00Z',
        symbol: '005930',
        title: '반도체 수출 지표, 예상치 상회 발표',
        sentiment: 'POSITIVE',
        impact: 0.65,
    },
    {
        id: '3',
        time: '2026-01-15T16:00:00Z',
        symbol: '005930',
        title: '경쟁사 신제품 출시로 인한 시장 점유율 우려',
        sentiment: 'NEGATIVE',
        impact: 0.45,
    }
];

export const generateMockTicks = (basePrice: number, count: number) => {
    let currentPrice = basePrice;
    return Array.from({ length: count }).map((_, i) => {
        const change = (Math.random() - 0.5) * 100;
        currentPrice += change;
        return {
            time: new Date(Date.now() - (count - i) * 1000).toISOString(),
            price: currentPrice,
            volume: Math.floor(Math.random() * 1000) + 100,
            type: Math.random() > 0.5 ? 'BUY' : 'SELL'
        };
    });
};
