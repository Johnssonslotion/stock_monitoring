import React, { useEffect, useState } from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { MOCK_SECTORS } from '../mocks/marketMocks';
import { fetchJson } from '../api';

interface MarketMapProps {
    filterType?: 'ALL' | 'STOCK' | 'ETF' | 'MARKET';
    onSymbolClick?: (symbol: string, name: string) => void;
}

const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        if (data.children) return null; // Sector header tooltip ignored
        return (
            <div className="glass p-3 rounded-lg border border-white/10 text-xs shadow-2xl backdrop-blur-md">
                <p className="font-bold text-white mb-1">{data.name} ({data.symbol})</p>
                {data.price && <p className="text-gray-300">Price: <span className="text-white">{data.price.toLocaleString()}</span></p>}
                <p className={data.change > 0 ? "text-red-400" : data.change < 0 ? "text-blue-400" : "text-gray-400"}>
                    Change: {data.change > 0 ? '+' : ''}{data.change}%
                </p>
                <p className="text-gray-400 mt-1">Cap: {(data.marketCap / 1e12).toFixed(1)}T</p>
            </div>
        );
    }
    return null;
};

const CustomizedContent = (props: any) => {
    const { x, y, width, height, change, symbol, name, onSymbolClick, children, onRenderSector } = props;

    const isSector = !!children;

    // Use effect to report sector geometry to parent (for overlay rendering)
    useEffect(() => {
        if (isSector && onRenderSector) {
            onRenderSector(name, { x, y, width, height });
        }
    }, [x, y, width, height, isSector, name, onRenderSector]);

    if (isSector) {
        return (
            <g>
                <rect
                    key={symbol}
                    data-symbol={symbol}
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    style={{
                        fill: 'transparent',
                        stroke: 'rgba(255,255,255,0.1)', // Subtle Sector Border
                        strokeWidth: 2,
                    }}
                />
            </g>
        );
    }

    // Adaptive LOD Logic
    const isTiny = width < 40 || height < 30;
    const isSmall = width < 80;
    const isMedium = width < 140;

    const fontSizeSymbol = Math.min(width / 4, 16);
    const fontSizeDetail = Math.min(width / 6, 11);

    return (
        <g
            onClick={() => onSymbolClick && onSymbolClick(symbol, name)}
            data-symbol={symbol}
            cursor="pointer"
            className="group"
        >
            <rect
                x={x}
                y={y}
                width={width}
                height={height}
                data-symbol={symbol}
                // Use SVG Gradients for Premium Look
                style={{
                    fill: change > 0 ? 'url(#gradient-positive)' : change < 0 ? 'url(#gradient-negative)' : 'url(#gradient-neutral)',
                    stroke: '#111827',
                    strokeWidth: 3,
                }}
                className="transition-colors duration-300 ease-out"
            />

            {/* Glossy Overlay Effect (Top half) for glass-like finish */}
            <rect
                x={x}
                y={y}
                width={width}
                height={height / 2}
                fill="url(#gradient-gloss)"
                style={{ opacity: 0.15, pointerEvents: 'none' }}
            />

            {/* Hover Highlight */}
            <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill="white"
                className="opacity-0 group-hover:opacity-10 transition-opacity duration-300 ease-out pointer-events-none"
            />

            {!isTiny && (
                <foreignObject x={x} y={y} width={width} height={height} style={{ pointerEvents: 'none' }}>
                    <div className="w-full h-full flex flex-col items-center justify-center p-1 overflow-hidden leading-tight">
                        {/* 1. Name (Primary, Large) */}
                        <span
                            className="text-white font-black tracking-tight"
                            style={{
                                fontSize: `${Math.min(width / 4, 18)}px`,
                                textShadow: '0 2px 4px rgba(0,0,0,0.5)'
                            }}
                        >
                            {name}
                        </span>

                        {/* 2. Symbol Code (Secondary, Small) */}
                        {!isSmall && (
                            <span className="text-white/60 text-[9px] font-mono mt-0.5">
                                {symbol}
                            </span>
                        )}

                        {/* 3. Change % (Visible on Medium+) */}
                        {!isSmall && (
                            <span
                                className="font-mono font-bold mt-0.5"
                                style={{
                                    fontSize: `${fontSizeDetail}px`,
                                    color: 'rgba(255,255,255,0.95)'
                                }}
                            >
                                {change > 0 ? '+' : ''}{change}%
                            </span>
                        )}

                        {/* 4. Price (Only visible on Large blocks) */}
                        {!isMedium && !isSmall && height > 80 && props.price && (
                            <span className="text-white/60 text-[9px] font-mono mt-0.5">
                                {props.price.toLocaleString()}
                            </span>
                        )}
                    </div>
                </foreignObject>
            )}
        </g>
    );
};

export const MarketMap: React.FC<MarketMapProps> = ({ filterType = 'ALL', onSymbolClick }) => {
    const [sectors, setSectors] = useState<any[]>(MOCK_SECTORS);
    const [sectorRects, setSectorRects] = useState<Record<string, { x: number, y: number, width: number, height: number }>>({});

    // Define Gradients globally for the map (injected into SVG)
    const Gradients = () => (
        <svg height="0" width="0" style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}>
            <defs>
                <linearGradient id="gradient-positive" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#ef4444" />
                    <stop offset="100%" stopColor="#b91c1c" />
                </linearGradient>
                <linearGradient id="gradient-negative" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#1d4ed8" />
                </linearGradient>
                <linearGradient id="gradient-neutral" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#4b5563" />
                    <stop offset="100%" stopColor="#1f2937" />
                </linearGradient>
                <linearGradient id="gradient-gloss" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="white" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="white" stopOpacity="0" />
                </linearGradient>
            </defs>
        </svg>
    );

    // Live Data Integration - Dynamic Sector Construction
    useEffect(() => {
        const fetchData = async () => {
            try {
                const market = 'kr';
                const data = await fetchJson<any>(`/market-map/${market}`);

                if (data && data.symbols && data.symbols.length > 0) {
                    // Define sector mapping based on kr_symbols.yaml structure
                    const sectorMap: Record<string, string[]> = {
                        '반도체 (Semiconductor)': ['005930', '000660', '042700'],
                        '이차전지 (Battery)': ['373220', '005490', '247540', '006400', '207940'],
                        '자동차 (Auto)': ['005380', '000270', '012330'],
                    };

                    // Create symbol lookup map
                    const symbolData = new Map(data.symbols.map((s: any) => [s.symbol, s]));

                    // Build hierarchical structure dynamically
                    const dynamicSectors = Object.entries(sectorMap).map(([sectorName, symbols]) => {
                        const children = symbols
                            .map(symbol => symbolData.get(symbol))
                            .filter(Boolean)
                            .map((stock: any) => ({
                                symbol: stock.symbol,
                                name: stock.name,
                                price: stock.price,
                                change: stock.change,
                                marketCap: stock.marketCap,
                            }));

                        return {
                            name: sectorName,
                            children,
                        };
                    }).filter(sector => sector.children.length > 0); // Only include sectors with data

                    if (dynamicSectors.length > 0) {
                        setSectors(dynamicSectors);
                    }
                }
            } catch (e) {
                console.warn("MarketMap Fetch failed, using Mock data", e);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 60000); // Poll every 60s
        return () => clearInterval(interval);
    }, [filterType]);

    const handleRenderSector = (name: string, rect: { x: number, y: number, width: number, height: number }) => {
        if (name === 'Market') return;
        setSectorRects(prev => {
            if (prev[name] && prev[name].x === rect.x && prev[name].y === rect.y && prev[name].width === rect.width && prev[name].height === rect.height) {
                return prev;
            }
            return { ...prev, [name]: rect };
        });
    };

    return (
        <div className="w-full h-full relative p-2">
            <Gradients />
            <ResponsiveContainer width="100%" height="100%">
                <Treemap
                    data={sectors}
                    dataKey="marketCap"
                    aspectRatio={4 / 3}
                    stroke="#111827"
                    content={<CustomizedContent onSymbolClick={onSymbolClick} onRenderSector={handleRenderSector} />}
                    isAnimationActive={false} // Disable Recharts default animation
                >
                    <Tooltip content={<CustomTooltip />} />
                </Treemap>
            </ResponsiveContainer>

            {/* Sector Overlays (Borders) */}
            <div className="absolute inset-0 pointer-events-none p-2">
                {Object.entries(sectorRects).map(([name, rect]) => (
                    <div
                        key={name}
                        style={{
                            position: 'absolute',
                            left: rect.x,
                            top: rect.y,
                            width: rect.width,
                            height: rect.height,
                            border: '1px solid rgba(255,255,255,0.05)',
                            boxShadow: 'inset 0 0 20px rgba(0,0,0,0.2)', // Inner depth for sectors
                            borderRadius: '4px',
                        }}
                    >
                        <div className="absolute top-0 right-0 bg-black/60 backdrop-blur-md px-1.5 py-0.5 text-[9px] text-gray-400 rounded-bl-lg border-b border-l border-white/5">
                            {name}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
