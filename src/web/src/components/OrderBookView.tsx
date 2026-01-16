import React, { useEffect, useState } from 'react';
import { ORDERBOOK_BY_SYMBOL, type OrderBook, type OrderBookLevel } from '../mocks/tradingMocks';

interface OrderBookViewProps {
    symbol: string;
    simple?: boolean; // New prop for simplified display
}

export const OrderBookView: React.FC<OrderBookViewProps> = ({ symbol, simple = false }) => {
    const [orderBook, setOrderBook] = useState<OrderBook | null>(null);

    useEffect(() => {
        // 심볼 변경 시 데이터 클리어 후 목업 데이터 로드
        setOrderBook(null);

        const timer = setTimeout(() => {
            const mockData = ORDERBOOK_BY_SYMBOL[symbol];
            if (mockData) {
                setOrderBook(mockData);
            }
        }, 100); // 실제 API 호출 시뮬레이션

        return () => clearTimeout(timer);
    }, [symbol]);

    if (!orderBook) {
        return (
            <div className="h-full flex items-center justify-center text-gray-500 text-xs">
                <div className="animate-pulse">Loading Order Book...</div>
            </div>
        );
    }

    const maxVolume = Math.max(
        ...orderBook.bids.map(b => b.volume),
        ...orderBook.asks.map(a => a.volume)
    );

    if (simple) {
        return (
            <div className="h-full flex flex-col bg-black/20 overflow-hidden">
                {/* Simple Header */}
                <div className="px-2 py-2 border-b border-white/5 flex justify-between items-center bg-white/5 shrink-0">
                    <span className="text-xs font-bold text-gray-400">ORDERBOOK</span>
                    <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-gray-500">Spread</span>
                        <span className="text-[10px] font-mono text-blue-300">{(orderBook.spread).toFixed(2)}%</span>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto scrollbar-hide flex flex-col text-[10px]">
                    {/* Asks (Sell) - Reversed */}
                    {[...orderBook.asks].reverse().map((ask, i) => (
                        <div key={`ask-${i}`} className="flex justify-between items-center px-2 py-1 hover:bg-white/5 border-b border-white/5">
                            <span className="font-mono text-gray-400">{ask.volume.toLocaleString()}</span>
                            <span className="font-mono text-blue-400 font-bold">{ask.price.toLocaleString()}</span>
                        </div>
                    ))}

                    <div className="h-0.5 bg-white/10 my-0" />

                    {/* Bids (Buy) */}
                    {orderBook.bids.map((bid, i) => (
                        <div key={`bid-${i}`} className="flex justify-between items-center px-2 py-1 hover:bg-white/5 border-b border-white/5">
                            <span className="font-mono text-red-400 font-bold">{bid.price.toLocaleString()}</span>
                            <span className="font-mono text-gray-400">{bid.volume.toLocaleString()}</span>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="px-3 py-2 bg-gray-800/50 border-b border-white/5 flex justify-between items-center shrink-0">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Order Book</span>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500">Spread:</span>
                    <span className={`text-xs font-mono ${orderBook.spread > 0.3 ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {orderBook.spread.toFixed(2)}%
                    </span>
                </div>
            </div>

            {/* JAR-SHAPED Order Book (항아리형) */}
            <div className="flex-1 flex flex-col gap-0.5 p-2 overflow-hidden">
                {/* Asks (매도) - Top to Bottom (높은가 -> 낮은가) */}
                {orderBook.asks.slice().reverse().map((ask, idx) => (
                    <JarRow key={`ask-${idx}`} level={ask} maxVolume={maxVolume} type="ask" />
                ))}

                {/* Spread Indicator */}
                <div className="h-6 flex items-center justify-center border-y border-yellow-500/20 bg-yellow-500/5 my-0.5">
                    <span className="text-[9px] text-yellow-400 font-mono">
                        ↕ SPREAD {orderBook.spread.toFixed(2)}%
                    </span>
                </div>

                {/* Bids (매수) - Top to Bottom (높은가 -> 낮은가) */}
                {orderBook.bids.map((bid, idx) => (
                    <JarRow key={`bid-${idx}`} level={bid} maxVolume={maxVolume} type="bid" />
                ))}
            </div>
        </div>
    );
};

interface JarRowProps {
    level: OrderBookLevel;
    maxVolume: number;
    type: 'bid' | 'ask';
}

const JarRow: React.FC<JarRowProps> = ({ level, maxVolume, type }) => {
    const widthPercent = (level.volume / maxVolume) * 100;
    const isBid = type === 'bid';

    // Original Jar Design (Default)
    return (
        <div className="relative h-5 flex items-center justify-center text-xs">
            {/* Left Bar (Bid) or Right Placeholder */}
            <div className="absolute left-0 right-1/2 h-full flex items-center justify-end pr-1">
                {isBid && (
                    <div
                        className="h-full bg-red-500/20 border-r border-red-500/40"
                        style={{ width: `${widthPercent}%` }}
                    />
                )}
                {isBid && (
                    <span className="absolute right-1 text-[10px] text-gray-400 font-mono">
                        {level.volume.toLocaleString()}
                    </span>
                )}
            </div>

            {/* Center Price */}
            <div className={`absolute inset-0 flex items-center justify-center font-mono font-bold z-10 ${isBid ? 'text-red-400' : 'text-blue-400'
                }`}>
                {level.price.toLocaleString()}
            </div>

            {/* Right Bar (Ask) or Left Placeholder */}
            <div className="absolute left-1/2 right-0 h-full flex items-center justify-start pl-1">
                {!isBid && (
                    <div
                        className="h-full bg-blue-500/20 border-l border-blue-500/40"
                        style={{ width: `${widthPercent}%` }}
                    />
                )}
                {!isBid && (
                    <span className="absolute left-1 text-[10px] text-gray-400 font-mono">
                        {level.volume.toLocaleString()}
                    </span>
                )}
            </div>
        </div>
    );
};
