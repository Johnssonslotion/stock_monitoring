import React, { useEffect, useRef, useState } from 'react';

interface VolumeBar {
    time: number;
    buyVolume: number; // Total Buy Volume
    buyWhale: number;  // Whale Part of Buy Volume
    sellVolume: number; // Total Sell Volume
    sellWhale: number;  // Whale Part of Sell Volume
}

const generateBar = () => {
    const isWhaleActivity = Math.random() > 0.85; // 15% chance of whale activity
    const baseVol = Math.random() * 500 + 100;

    // Whale adds massive volume if active
    const whaleBuy = isWhaleActivity && Math.random() > 0.5 ? baseVol * (Math.random() * 3 + 2) : 0;
    const whaleSell = isWhaleActivity && Math.random() <= 0.5 ? baseVol * (Math.random() * 3 + 2) : 0;

    const totalBuy = baseVol * Math.random() + whaleBuy;
    const totalSell = baseVol * Math.random() + whaleSell;

    return {
        time: Date.now(),
        buyVolume: totalBuy,
        buyWhale: whaleBuy,
        sellVolume: totalSell,
        sellWhale: whaleSell,
    };
};

export const VolumeHistogram: React.FC = () => {
    const [bars, setBars] = useState<VolumeBar[]>(() =>
        Array.from({ length: 40 }, () => generateBar())
    );
    const containerRef = useRef<HTMLDivElement>(null);

    // Real-time Update
    useEffect(() => {
        const interval = setInterval(() => {
            setBars(prev => {
                const newBar = generateBar();
                return [...prev.slice(1), newBar];
            });
        }, 1000); // 1-second update

        return () => clearInterval(interval);
    }, []);

    // Calculate max volume for scale
    const maxVol = Math.max(...bars.map(b => Math.max(b.buyVolume, b.sellVolume)), 500);

    return (
        <div className="w-full h-full flex flex-col relative bg-black/20" ref={containerRef}>
            <div className="absolute top-1 left-2 z-10 text-[10px] font-bold text-gray-500 uppercase flex gap-2">
                <span>Volume Flow</span>
                <span className="text-red-400">Buy</span>
                <span className="text-blue-400">Sell</span>
            </div>

            <div className="flex-1 flex items-end justify-between gap-[2px] px-1 py-1 h-full items-center">
                {bars.map((bar, i) => {
                    // Heights
                    const buyTotalH = (bar.buyVolume / maxVol) * 45;
                    const buyWhaleH = (bar.buyWhale / maxVol) * 45;

                    const sellTotalH = (bar.sellVolume / maxVol) * 45;
                    const sellWhaleH = (bar.sellWhale / maxVol) * 45;

                    return (
                        <div key={i} className="flex-1 flex flex-col items-center h-full justify-center group relative min-w-[3px]">
                            {/* Zero Line */}
                            <div className="absolute w-full h-[1px] bg-white/10" />

                            {/* UP: Buy Bar */}
                            <div className="w-full relative flex flex-col-reverse items-center" style={{ height: `${Math.max(buyTotalH, 1)}%`, marginBottom: '1px' }}>
                                {/* Retail Base (Light) */}
                                <div className="absolute inset-0 bg-red-500/30 rounded-t-sm" />
                                {/* Whale Core (Solid + Neon) */}
                                <div
                                    className="w-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] z-10 rounded-t-sm transition-all duration-300"
                                    style={{ height: `${(buyWhaleH / buyTotalH) * 100}%` }}
                                />
                            </div>

                            {/* DOWN: Sell Bar */}
                            <div className="w-full relative flex flex-col items-center" style={{ height: `${Math.max(sellTotalH, 1)}%`, marginTop: '1px' }}>
                                {/* Retail Base (Light) */}
                                <div className="absolute inset-0 bg-blue-500/30 rounded-b-sm" />
                                {/* Whale Core (Solid + Neon) */}
                                <div
                                    className="w-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)] z-10 rounded-b-sm transition-all duration-300"
                                    style={{ height: `${(sellWhaleH / sellTotalH) * 100}%` }}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
