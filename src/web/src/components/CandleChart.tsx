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
    interval?: string; // Add interval prop for empty state messaging
}

export const CandleChart: React.FC<CandleChartProps> = ({ data, symbol, interval = '1d' }) => {
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
            // Step 1: Format time values first
            const formattedData = data.map((item: any) => {
                // Handle time format: Prefer YYYY-MM-DD for daily data to avoid timezone shift
                let time: any = item.time;
                if (typeof item.time === 'string' && item.time.includes('T')) {
                    const date = new Date(item.time);
                    // Convert to YYYY-MM-DD string
                    // Note: Using UTC methods to align with the +00:00 offset from API
                    const year = date.getUTCFullYear();
                    const month = (date.getUTCMonth() + 1).toString().padStart(2, '0');
                    const day = date.getUTCDate().toString().padStart(2, '0');
                    time = `${year}-${month}-${day}`;
                } else if (typeof item.time === 'string') {
                    time = new Date(item.time).getTime() / 1000;
                }

                return {
                    ...item,
                    time: time
                };
            });

            // Step 2: Deduplicate based on formatted time (keep last occurrence)
            const uniqueMap = new Map();
            formattedData.forEach(item => uniqueMap.set(item.time, item));

            // Step 3:Sort by time
            const sortedData = Array.from(uniqueMap.values())
                .sort((a: any, b: any) => {
                    // For YYYY-MM-DD strings, use string comparison
                    if (typeof a.time === 'string' && typeof b.time === 'string') {
                        return a.time.localeCompare(b.time);
                    }
                    // For timestamps, numeric comparison
                    return Number(a.time) - Number(b.time);
                });

            console.log(`📊 Setting ${sortedData.length} candles for ${symbol}`);
            seriesRef.current.setData(sortedData);
            chartRef.current?.timeScale().fitContent();
        }
    }, [data, symbol]);

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

    // Empty State when no data available
    if (!data || data.length === 0) {
        return (
            <div className="w-full h-full flex items-center justify-center">
                <div className="glassmorphism p-8 rounded-2xl text-center max-w-md">
                    <div className="text-6xl mb-4">📊</div>
                    <h3 className="text-xl font-bold text-white mb-2">No Data Available</h3>
                    <p className="text-gray-400 mb-4">
                        No candle data found for <span className="text-blue-400 font-mono">{symbol}</span> at <span className="text-green-400 font-mono">{interval}</span> interval.
                    </p>
                    <div className="text-sm text-gray-500 bg-black/20 rounded-lg p-3 border border-white/5">
                        <strong>Tip:</strong> Try switching to <span className="text-yellow-400">1D</span> (Daily) timeframe for historical data.
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-full flex flex-col">
            <div ref={chartContainerRef} className="flex-1 w-full relative" />
        </div>
    );
};
