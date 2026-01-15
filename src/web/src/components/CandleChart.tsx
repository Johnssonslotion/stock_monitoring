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

        // Cleanup function ref
        let chart: IChartApi | null = null;
        let resizeObserver: ResizeObserver | null = null;

        const initChart = () => {
            if (!chartContainerRef.current) return;
            const { clientWidth, clientHeight } = chartContainerRef.current;

            // Guard: Do not initialize if dimensions are invalid
            if (clientWidth <= 0 || clientHeight <= 0) return;

            if (chart) {
                // If chart exists, just resize
                chart.applyOptions({ width: clientWidth, height: clientHeight });
                return;
            }

            // Create Chart
            chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: 'transparent' },
                    textColor: '#9CA3AF',
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                width: clientWidth,
                height: clientHeight,
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
                upColor: '#ef4444',
                downColor: '#3b82f6',
                borderVisible: false,
                wickUpColor: '#ef4444',
                wickDownColor: '#3b82f6',
            });

            seriesRef.current = candlestickSeries;
            chartRef.current = chart;

            // Trigger data update if data exists
            if (data.length > 0) {
                updateData(data);
            }
        };

        // Observer to handle resize and delayed init
        resizeObserver = new ResizeObserver(() => {
            initChart();
        });
        resizeObserver.observe(chartContainerRef.current);

        return () => {
            if (resizeObserver) resizeObserver.disconnect();
            if (chart) chart.remove();
            chartRef.current = null;
            seriesRef.current = null;
        };
    }, []); // Run once on mount, internal logic handles deps

    // Helper to update data safely
    const updateData = (newData: CandleData[]) => {
        if (!seriesRef.current || newData.length === 0) return;

        try {
            const formattedData = newData
                .map((item: any) => {
                    let time: any = item.time;
                    // Robust time parsing
                    if (typeof item.time === 'string') {
                        if (item.time.includes('T')) {
                            const date = new Date(item.time);
                            if (isNaN(date.getTime())) return null; // Skip invalid
                            const year = date.getUTCFullYear();
                            const month = (date.getUTCMonth() + 1).toString().padStart(2, '0');
                            const day = date.getUTCDate().toString().padStart(2, '0');
                            time = `${year}-${month}-${day}`;
                        } else {
                            // Assume simplified string or timestamp
                            const date = new Date(item.time);
                            if (!isNaN(date.getTime())) {
                                time = date.getTime() / 1000;
                            }
                        }
                    }
                    if (!item.open || !item.high || !item.low || !item.close) return null;

                    return { ...item, time: time };
                })
                .filter(item => item !== null); // Filter invalid

            // Deduplicate
            const uniqueMap = new Map();
            formattedData.forEach((item: any) => uniqueMap.set(item.time, item));

            const sortedData = Array.from(uniqueMap.values())
                .sort((a: any, b: any) => {
                    if (typeof a.time === 'string' && typeof b.time === 'string') {
                        return a.time.localeCompare(b.time);
                    }
                    return Number(a.time) - Number(b.time);
                });

            console.log(`📊 Rendering ${sortedData.length} valid candles`);
            seriesRef.current.setData(sortedData);
            chartRef.current?.timeScale().fitContent();
        } catch (e) {
            console.error("Chart Rendering Error:", e);
        }
    };

    // React to data changes
    useEffect(() => {
        if (chartRef.current && seriesRef.current) {
            updateData(data);
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
