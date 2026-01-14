import React, { useState, useEffect, useMemo } from 'react';
import Plot from 'react-plotly.js';
import { useApi } from '../hooks/useApi';
import { BarChart2, RefreshCw, TrendingUp, Activity } from 'lucide-react';

const API_HOST = import.meta.env.VITE_API_HOST || window.location.hostname;
const API_PORT = import.meta.env.VITE_API_PORT || '8000';
const API_SERVER = `http://${API_HOST}:${API_PORT}`;

const CandleChart = ({ symbol = 'QQQ' }) => {
    const { request, loading, error } = useApi(API_SERVER);
    const [data, setData] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [timeRange, setTimeRange] = useState(100); // Number of candles

    const fetchData = async (limit = timeRange) => {
        const result = await request(`/api/v1/candles/${symbol}?limit=${limit}`);
        if (result) {
            setData(result);
            setLastUpdated(new Date());
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, [symbol, timeRange]);

    // Calculate Moving Averages
    const calculateMA = (prices, period) => {
        const ma = [];
        for (let i = 0; i < prices.length; i++) {
            if (i < period - 1) {
                ma.push(null);
            } else {
                const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
                ma.push(sum / period);
            }
        }
        return ma;
    };

    // Price Metrics
    const priceMetrics = useMemo(() => {
        if (data.length === 0) return null;
        const latest = data[data.length - 1];
        const first = data[0];
        const change = latest.close - first.open;
        const changePercent = ((change / first.open) * 100).toFixed(2);
        return {
            current: latest.close,
            open: latest.open,
            high: Math.max(...data.map(d => d.high)),
            low: Math.min(...data.map(d => d.low)),
            volume: data.reduce((sum, d) => sum + d.volume, 0),
            change,
            changePercent,
            isUp: change >= 0
        };
    }, [data]);

    // Plotly Data
    const plotData = useMemo(() => {
        if (data.length === 0) return [];

        const times = data.map(d => d.time);
        const closes = data.map(d => d.close);
        const ma5 = calculateMA(closes, 5);
        const ma20 = calculateMA(closes, 20);

        return [
            // Candlestick
            {
                x: times,
                close: closes,
                decreasing: { line: { color: '#ef4444' } },
                increasing: { line: { color: '#22c55e' } },
                high: data.map(d => d.high),
                low: data.map(d => d.low),
                open: data.map(d => d.open),
                type: 'candlestick',
                name: symbol,
                xaxis: 'x',
                yaxis: 'y',
                hoverinfo: 'skip' // Custom tooltip
            },
            // MA5
            {
                x: times,
                y: ma5,
                type: 'scatter',
                mode: 'lines',
                name: 'MA5',
                line: { color: '#3b82f6', width: 1 },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: 'MA5: %{y:.2f}<extra></extra>'
            },
            // MA20
            {
                x: times,
                y: ma20,
                type: 'scatter',
                mode: 'lines',
                name: 'MA20',
                line: { color: '#f97316', width: 1 },
                xaxis: 'x',
                yaxis: 'y',
                hovertemplate: 'MA20: %{y:.2f}<extra></extra>'
            },
            // Volume
            {
                x: times,
                y: data.map(d => d.volume),
                type: 'bar',
                name: 'Volume',
                marker: {
                    color: data.map((d, i) => {
                        if (i === 0) return '#64748b';
                        return d.close >= data[i - 1].close ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)';
                    })
                },
                xaxis: 'x',
                yaxis: 'y2',
                hovertemplate: 'Vol: %{y:,.0f}<extra></extra>'
            }
        ];
    }, [data, symbol]);

    const layout = {
        dragmode: 'zoom',
        hovermode: 'x unified',
        showlegend: true,
        legend: { x: 0, y: 1.1, orientation: 'h', bgcolor: 'rgba(0,0,0,0)' },
        grid: { rows: 2, columns: 1, pattern: 'independent', roworder: 'top to bottom' },
        xaxis: {
            rangeslider: { visible: false },
            type: 'date',
            gridcolor: '#333',
            zerolinecolor: '#333',
            showticklabels: true
        },
        yaxis: {
            domain: [0.25, 1],
            gridcolor: '#333',
            zerolinecolor: '#333',
            fixedrange: false
        },
        yaxis2: {
            domain: [0, 0.2],
            gridcolor: '#333',
            showticklabels: false
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1', size: 11 },
        margin: { l: 50, r: 20, t: 10, b: 30 },
        height: 500
    };

    return (
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', padding: '15px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <BarChart2 size={18} color="var(--accent-color)" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{symbol} Chart</h3>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {/* Time Range Buttons */}
                    {[50, 100, 200].map(range => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            className={timeRange === range ? 'active' : ''}
                            style={{
                                background: timeRange === range ? 'var(--accent-color)' : 'rgba(255,255,255,0.1)',
                                border: 'none',
                                padding: '4px 10px',
                                borderRadius: '4px',
                                color: 'inherit',
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                                transition: 'all 0.2s'
                            }}
                        >
                            {range}
                        </button>
                    ))}
                    <button onClick={() => fetchData()} className="icon-button" style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                        <RefreshCw size={14} className={loading ? 'spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Price Metrics Panel */}
            {
                priceMetrics && (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                        gap: '10px',
                        marginBottom: '15px',
                        padding: '12px',
                        background: 'rgba(255,255,255,0.03)',
                        borderRadius: '8px'
                    }}>
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Current</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: priceMetrics.isUp ? 'var(--success-color)' : 'var(--danger-color)' }}>
                                ${priceMetrics.current.toFixed(2)}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: priceMetrics.isUp ? 'var(--success-color)' : 'var(--danger-color)' }}>
                                {priceMetrics.isUp ? '▲' : '▼'} {priceMetrics.changePercent}%
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>High</div>
                            <div style={{ fontSize: '0.95rem' }}>${priceMetrics.high.toFixed(2)}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Low</div>
                            <div style={{ fontSize: '0.95rem' }}>${priceMetrics.low.toFixed(2)}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Volume</div>
                            <div style={{ fontSize: '0.95rem' }}>{(priceMetrics.volume / 1000000).toFixed(2)}M</div>
                        </div>
                    </div>
                )
            }

            {/* Chart */}
            <div style={{ flex: 1, position: 'relative', minHeight: '500px' }}>
                {error && (
                    <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--danger-color)' }}>
                        Failed to load: {error}
                    </div>
                )}
                {data.length > 0 ? (
                    <Plot
                        data={plotData}
                        layout={layout}
                        config={{
                            responsive: true,
                            displayModeBar: true,
                            displaylogo: false,
                            scrollZoom: true, // Enable scroll zoom
                            modeBarButtonsToAdd: ['resetScale2d'],
                            modeBarButtonsToRemove: ['lasso2d', 'select2d']
                        }}
                        style={{ width: '100%', height: '100%' }}
                    />
                ) : (
                    !loading && !error && (
                        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--text-secondary)' }}>
                            No data available
                        </div>
                    )
                )}
            </div>
        </div >
    );
};

export default CandleChart;
