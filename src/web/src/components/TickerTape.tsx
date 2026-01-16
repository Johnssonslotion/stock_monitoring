import React, { useEffect, useState } from 'react';
import { MOCK_SECTORS } from '../mocks/marketMocks';

export const TickerTape: React.FC = () => {
    const [items, setItems] = useState<any[]>([]);

    useEffect(() => {
        // Flatten all symbols from sectors for the ticker
        const allSymbols = MOCK_SECTORS.flatMap(sector => sector.children || []);
        // Duplicate list for seamless scrolling illusion
        setItems([...allSymbols, ...allSymbols, ...allSymbols]);
    }, []);

    return (
        <div className="w-full bg-black/60 border-b border-white/5 overflow-hidden flex items-center h-8 relative z-20 backdrop-blur-sm">
            <div className="flex animate-ticker whitespace-nowrap gap-8 px-4 text-xs">
                {items.map((item, idx) => (
                    <div key={`${item.symbol}-${idx}`} className="flex items-center gap-2">
                        <span className="font-bold text-gray-300">{item.name}</span>
                        <span className={`font-mono ${item.change > 0 ? 'text-red-400' : 'text-blue-400'}`}>
                            {item.change > 0 ? '▲' : '▼'} {Math.abs(item.change)}%
                        </span>
                    </div>
                ))}
            </div>

            {/* Gradient Overlay for Fade Effect */}
            <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-black via-black/80 to-transparent pointer-events-none" />
            <div className="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-black via-black/80 to-transparent pointer-events-none" />
        </div>
    );
};
