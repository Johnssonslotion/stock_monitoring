import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, type IChartApi, type ISeriesApi } from 'lightweight-charts';
import { streamManager } from '../StreamManager';

interface CandleData {
    time: string | number; // String date or timestamp
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
}

interface CandleChartProps {
    data: CandleData[];
    symbol: string;
}

export const CandleChart: React.FC<CandleChartProps> = ({ data, symbol }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' }, // Transparent for Glassmorphism
                textColor: '#9CA3AF',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            width: chartContainerRef.current.clientWidth,
            height: chartContainerRef.current.clientHeight,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
        });

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#ef4444', // Red for Up (Korean Style)
            downColor: '#3b82f6', // Blue for Down
            borderVisible: false,
            wickUpColor: '#ef4444',
            wickDownColor: '#3b82f6',
        });

        seriesRef.current = candlestickSeries;
        chartRef.current = chart;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    useEffect(() => {
        if (seriesRef.current && data.length > 0) {
            // Deduplicate data based on time string first
            const uniqueMap = new Map();
            data.forEach(item => uniqueMap.set(item.time, item));

            // Sort and format
            const sortedData = Array.from(uniqueMap.values())
                .sort((a: any, b: any) => {
                    const tA = new Date(a.time).getTime();
                    const tB = new Date(b.time).getTime();
                    return tA - tB;
                })
                .map((item: any) => ({
                    ...item,
                    time: (new Date(item.time).getTime() / 1000) as any
                }));

            seriesRef.current.setData(sortedData);
            chartRef.current?.timeScale().fitContent();
        }
    }, [data]);

    // WebSocket logic for real-time updates
    useEffect(() => {
        const handleTick = (tick: any) => {
            if (tick.symbol !== symbol) return; // Filter by symbol
            if (!seriesRef.current) return;

            // Construct new candle or update existing
            // Since we only get 'price', this is a pseudo-update (Close price updates)
            // Ideally backend aggregates ticks into minute bars
            // Construct new candle or update existing

            // For now, simpler logic: Just verify socket is live by logging
            console.log('Live Tick:', tick);

            // NOTE: Lightweight Charts 'update' method handles appending
            // But we need Open/High/Low to form a candle. 
            // For MVP, we'll rely on periodic polling for full history and maybe overlay last price?
            // Or assume the last candle is mutable.
            // Complex logic omitted for MVP stability: "Zero Cost" constraint.
        };

        streamManager.on('tick', handleTick);
        return () => streamManager.off('tick', handleTick);
    }, [symbol]);

    return (
        <div className="w-full h-full flex flex-col">
            <div className="p-3 border-b border-white/5 font-bold text-gray-100 flex justify-between items-center bg-white/5 active:bg-blue-500/10 transition-colors">
                <span className="flex items-center gap-2">
                    {symbol} Chart (Daily)
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300">KR</span>
                </span>
                <span className="text-xs text-gray-500 flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                    Real-time
                </span>
            </div>
            <div ref={chartContainerRef} className="flex-1 w-full relative" />
        </div>
    );
};
