import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { clsx } from 'clsx';

interface MarketItem {
    symbol: string;
    name: string;
    marketCap: number;
    price: number;
    prevPrice: number;
    change: number; // Legacy, will be overridden
    size: number; // For Recharts
    category?: string;
}

const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div className="glass p-3 rounded-lg border border-white/10 text-xs">
                <p className="font-bold text-white mb-1">{data.name} ({data.symbol})</p>
                <p className="text-gray-300">Price: <span className="text-white">{data.price.toLocaleString()}</span></p>
                <p className={data.change > 0 ? "text-red-400" : "text-blue-400"}>
                    Change: {data.change}%
                </p>
                <p className="text-gray-400 mt-1">Vol: {Math.floor(data.marketCap).toLocaleString()}</p>
            </div>
        );
    }
    return null;
};

const CustomizedContent = (props: any) => {
    const { depth, x, y, width, height, change, symbol, name } = props;

    return (
        <g>
            <rect
                x={x}
                y={y}
                width={width}
                height={height}
                style={{
                    fill: change > 0 ? '#ef4444' : change < 0 ? '#3b82f6' : '#374151',
                    fillOpacity: 0.6 + (Math.min(Math.abs(change), 5) / 10), // Opacity based on magnitude
                    stroke: '#fff',
                    strokeWidth: 2 / (depth + 1e-10),
                    strokeOpacity: 0.1,
                }}
                className="transition-all duration-150 hover:fill-opacity-100 cursor-pointer"
            />
            {width > 50 && height > 30 && (
                <foreignObject x={x} y={y} width={width} height={height}>
                    <div className="w-full h-full flex flex-col items-center justify-center text-white text-[10px] overflow-hidden p-1 pointer-events-none">
                        <span className="font-bold truncate" style={{ fontSize: width > 80 ? '11px' : '9px' }}>{name}</span>
                        <span className="text-[9px] text-gray-300 transform scale-90">{symbol}</span>
                        <span className={clsx("font-medium mt-0.5", change > 0 ? "text-red-100" : "text-blue-100")}>
                            {change > 0 ? '+' : ''}{change}%
                        </span>
                    </div>
                </foreignObject>
            )}
        </g>
    );
};

interface MarketMapProps {
    filterType?: 'ALL' | 'STOCK' | 'ETF' | 'MARKET';
}

export const MarketMap: React.FC<MarketMapProps> = ({ filterType = 'ALL' }) => {
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [useLogScale, setUseLogScale] = useState(false);

    const fetchMap = async () => {
        try {
            // Check connection first or rely on axios failure
            const res = await axios.get('/market-map/kr');

            // Filter by Category
            let items = res.data.symbols as MarketItem[];
            if (filterType !== 'ALL') {
                items = items.filter(item => item.category === filterType);
            }

            // Format for Recharts
            const formatted = items.map((item: MarketItem) => {
                const current = item.price;
                const prev = item.prevPrice || current;
                const calcChange = prev !== 0 ? ((current - prev) / prev * 100) : 0;

                return {
                    ...item,
                    change: parseFloat(calcChange.toFixed(2)),
                    size: useLogScale ? Math.log(item.marketCap + 1) : item.marketCap
                };
            });

            setData([{ name: filterType, children: formatted }]);
            setError(false);
        } catch (e) {
            console.error("Market Map Fetch Error:", e);
            setError(true);
            setData([]); // Clear data on error to avoid stale state if requested
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMap();
        const interval = setInterval(fetchMap, 5000);
        return () => clearInterval(interval);
    }, [useLogScale, filterType]);

    if (loading && data.length === 0) return <div className="text-gray-500 p-4 text-xs">Loading Market Map...</div>;

    if (error || data.length === 0 || (data[0]?.children?.length === 0)) {
        return (
            <div className="h-full w-full flex flex-col items-center justify-center text-center p-4">
                <div className="text-4xl mb-2 opacity-30">🗺️</div>
                <div className="text-sm font-bold text-gray-400">Map Unavailable</div>
                <div className="text-xs text-gray-600 mt-1">Disconnected or No Data</div>
            </div>
        );
    }

    return (
        <div className="h-full w-full relative group">
            {/* Log Scale Toggle (Visible on Hover) */}
            <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                    onClick={() => setUseLogScale(!useLogScale)}
                    className={clsx(
                        "text-[10px] px-2 py-1 rounded border backdrop-blur-sm transition-colors",
                        useLogScale
                            ? "bg-blue-500/20 border-blue-500 text-blue-200"
                            : "bg-black/20 border-white/10 text-gray-400 hover:bg-white/10"
                    )}
                >
                    {useLogScale ? "Log Scale: ON" : "Log Scale: OFF"}
                </button>
            </div>

            <ResponsiveContainer width="100%" height="100%">
                <Treemap
                    data={data}
                    dataKey="size"
                    stroke="#fff"
                    fill="#8884d8"
                    content={<CustomizedContent />}
                    animationDuration={500}
                >
                    <Tooltip content={<CustomTooltip />} />
                </Treemap>
            </ResponsiveContainer>
        </div>
    );
};
