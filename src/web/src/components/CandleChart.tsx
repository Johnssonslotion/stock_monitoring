import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import { createChart, ColorType } from 'lightweight-charts';
import { RefreshCcw, Plus, Minus } from 'lucide-react';
import { streamManager } from '../StreamManager';

interface CandleData {
    time: string | number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
}

interface CandleChartProps {
    data: CandleData[];
    symbol: string;
    interval?: string;
}

export const CandleChart: React.FC<CandleChartProps> = ({ data, symbol, interval = '1d' }) => {
    const [container, setContainer] = useState<HTMLElement | null>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const mainSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

    // Track state for zoom/viewport
    const prevSymbol = useRef<string>(symbol);
    const prevInterval = useRef<string>(interval);

    // Helper: Check if market is currently active (Today & < 15:30)
    const isMarketActive = (lastCandleTime: number): boolean => {
        const now = new Date();
        const lastDate = new Date(lastCandleTime * 1000);

        // Check if same day
        const isSameDay = now.getDate() === lastDate.getDate() &&
            now.getMonth() === lastDate.getMonth() &&
            now.getFullYear() === lastDate.getFullYear();

        if (!isSameDay) return false;

        // Check if before close (15:30)
        const currentMinutes = now.getHours() * 60 + now.getMinutes();
        const closeMinutes = 15 * 60 + 30; // 15:30

        return currentMinutes < closeMinutes;
    };

    const updateData = (newData: CandleData[]) => {
        if (!mainSeriesRef.current || !volumeSeriesRef.current || newData.length === 0) return;

        try {
            // Process Data
            const processedData = newData.map((item: any) => {
                let time: any = item.time;
                if (typeof item.time === 'string') {
                    const date = new Date(item.time);
                    if (!isNaN(date.getTime())) {
                        // Use timestamp for uniform sorting
                        time = Math.floor(date.getTime() / 1000);
                    }
                }
                return { ...item, time };
            })
                .filter(item => item.open !== undefined && item.time !== undefined)
                .sort((a: any, b: any) => a.time - b.time);

            // Deduplicate timestamps
            const uniqueMap = new Map();
            processedData.forEach((item: any) => uniqueMap.set(item.time, item));
            const uniqueData = Array.from(uniqueMap.values());

            // Set Candle Data
            mainSeriesRef.current.setData(uniqueData);

            // Set Volume Data
            const volumeData = uniqueData.map((d: any, i: number) => {
                const prevClose = i > 0 ? uniqueData[i - 1].close : d.open;
                const isUp = d.close >= d.open;
                return {
                    time: d.time,
                    value: d.volume || 0,
                    // Red for Up (Korean standard), Blue for Down
                    color: isUp ? 'rgba(239, 68, 68, 0.5)' : 'rgba(59, 130, 246, 0.5)'
                };
            });
            volumeSeriesRef.current.setData(volumeData);

        } catch (e) {
            console.error("Chart Data Update Error:", e);
        }
    };

    // Container Ref
    const chartContainerRef = useCallback((node: HTMLDivElement | null) => {
        if (node) setContainer(node);
    }, []);

    // Create Chart
    useEffect(() => {
        if (!container) return;
        if (chartRef.current) return;

        console.log("Creating Chart Instance");

        const chart = createChart(container, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#9ca3af',
                fontFamily: 'Inter, sans-serif'
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' }
            },
            width: container.clientWidth,
            height: container.clientHeight,
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: '#2b2b43',
                rightOffset: 12,
                minBarSpacing: 6, // Fix: Prevent overlaps
                fixLeftEdge: true,
                fixRightEdge: true,
                allowShiftVisibleRangeOnWhitespaceReplacement: true,
            },
            rightPriceScale: {
                borderColor: '#2b2b43',
                scaleMargins: { top: 0.1, bottom: 0.2 } // Leave bottom 20% for volume
            }
        });

        // Series 1: Candles
        const mainSeries = chart.addCandlestickSeries({
            upColor: '#ef4444',
            downColor: '#3b82f6',
            borderVisible: false,
            wickUpColor: '#ef4444',
            wickDownColor: '#3b82f6',
        });
        mainSeriesRef.current = mainSeries;

        // Series 2: Volume
        const volumeSeries = chart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: '', // Same scale but positioned manually
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 }, // Bottom 20%
        });
        volumeSeriesRef.current = volumeSeries;

        chartRef.current = chart;

        // Resize
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                if (entry.contentRect.width > 0) {
                    chart.applyOptions({
                        width: entry.contentRect.width,
                        height: entry.contentRect.height
                    });
                }
            }
        });
        resizeObserver.observe(container);

        return () => {
            resizeObserver.disconnect();
            chart.remove();
            chartRef.current = null;
        };
    }, [container]);

    // Handle Logic
    useEffect(() => {
        if (!chartRef.current || !data || data.length === 0) return;

        updateData(data);

        const isNewContext = prevSymbol.current !== symbol || prevInterval.current !== interval;

        if (isNewContext) {
            handleViewportReset();
            prevSymbol.current = symbol;
            prevInterval.current = interval;
        }

    }, [data, symbol, interval]);

    const handleViewportReset = () => {
        if (!chartRef.current || data.length === 0) return;

        const lastCandle = data[data.length - 1];
        const lastTime = typeof lastCandle.time === 'number'
            ? lastCandle.time
            : new Date(lastCandle.time).getTime() / 1000;

        if (interval === '1m') {
            // 1분봉 전략
            const isActive = isMarketActive(lastTime);

            if (isActive) {
                // Active Market: Show whitespace until 15:30
                const now = new Date();
                const closeTime = new Date(now);
                closeTime.setHours(15, 30, 0, 0);

                const diffSec = (closeTime.getTime() / 1000) - lastTime;

                // Extra bars needed to fill until 15:30
                const extraBars = Math.max(10, Math.floor(diffSec / 60) + 5);

                // Show recent 120 bars (2 hours) + Whitespace
                chartRef.current.timeScale().setVisibleLogicalRange({
                    from: data.length - 120,
                    to: data.length + extraBars
                });
            } else {
                // Closed Market: Align to right (No gap)
                chartRef.current.timeScale().setVisibleLogicalRange({
                    from: data.length - 120, // Initial View: Last 2 hours
                    to: data.length + 2      // Tiny margin
                });
            }
        } else {
            // Daily/Intervals
            if (data.length > 200) {
                chartRef.current.timeScale().setVisibleLogicalRange({
                    from: data.length - 150,
                    to: data.length + 5
                });
            } else {
                chartRef.current.timeScale().fitContent();
            }
        }
    };

    // Manual Zoom
    const handleZoom = (direction: 'in' | 'out') => {
        if (!chartRef.current) return;
        const timeScale = chartRef.current.timeScale();
        const currentRange = timeScale.getVisibleLogicalRange();

        if (!currentRange) return;

        // Simple Logic: Shrink/Expand range by 20%
        const range = currentRange.to - currentRange.from;
        const delta = range * 0.2;

        if (direction === 'in') {
            timeScale.setVisibleLogicalRange({
                from: currentRange.from + delta,
                to: currentRange.to
            });
        } else {
            timeScale.setVisibleLogicalRange({
                from: currentRange.from - delta,
                to: currentRange.to
            });
        }
    };

    if (!data || data.length === 0) {
        return <div className="w-full h-full flex items-center justify-center text-gray-500">No Data</div>;
    }

    return (
        <div className="w-full h-full min-h-[300px] relative group flex-1 flex flex-col">
            <div ref={chartContainerRef} className="absolute inset-0 z-0" />

            {/* Controls */}
            <div className="absolute top-3 right-3 z-10 flex gap-1 opacity-100">
                <button onClick={() => handleZoom('in')} className="p-1.5 bg-gray-800/80 hover:bg-gray-700 text-white rounded border border-white/10 shadow-lg"><Plus size={16} /></button>
                <button onClick={() => handleZoom('out')} className="p-1.5 bg-gray-800/80 hover:bg-gray-700 text-white rounded border border-white/10 shadow-lg"><Minus size={16} /></button>
                <button onClick={() => chartRef.current?.timeScale().fitContent()} className="p-1.5 bg-gray-800/80 hover:bg-gray-700 text-white rounded border border-white/10 shadow-lg"><RefreshCcw size={16} /></button>
            </div>
        </div>
    );
};

export default CandleChart;
