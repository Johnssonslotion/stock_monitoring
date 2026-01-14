import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { useApi } from '../hooks/useApi';
import { Grid3x3, RefreshCw, TrendingUp } from 'lucide-react';

const API_HOST = import.meta.env.VITE_API_HOST || window.location.hostname;
const API_PORT = import.meta.env.VITE_API_PORT || '8000';
const API_SERVER = `http://${API_HOST}:${API_PORT}`;

const MarketMap = ({ onSymbolClick }) => {
    const { request, loading, error } = useApi(API_SERVER);
    const [data, setData] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [selectedMarket, setSelectedMarket] = useState('us'); // 'kr' or 'us'
    const [currency, setCurrency] = useState('USD');

    const fetchData = async (market = selectedMarket) => {
        const result = await request(`/api/v1/market-map/${market}`);
        if (result && result.symbols) {
            setData(result.symbols);
            setCurrency(result.currency || 'USD');
            setLastUpdated(new Date());
        }
    };

    useEffect(() => {
        fetchData(selectedMarket);
        // Update every 5 minutes
        const interval = setInterval(() => fetchData(selectedMarket), 300000);
        return () => clearInterval(interval);
    }, [selectedMarket]);

    const handleMarketSwitch = (market) => {
        setSelectedMarket(market);
        fetchData(market);
    };

    // Prepare Plotly Treemap data
    const plotData = () => {
        if (data.length === 0) return [];

        const labels = data.map(d => d.symbol.replace('.KS', '')); // Remove .KS for display
        const parents = data.map(() => ""); // All root level
        const values = data.map(d => d.marketCap);
        const changes = data.map(d => d.change);
        const activeStatus = data.map(d => d.isActive);

        // Custom text with active indicator
        const customText = data.map(d =>
            `${d.symbol.replace('.KS', '')}<br>${d.change >= 0 ? '+' : ''}${d.change.toFixed(2)}%${d.isActive ? ' ⭐' : ''}`
        );

        // Currency formatting based on market
        const formatMarketCap = (cap) => {
            if (currency === 'KRW') {
                return `₩${(cap / 1e12).toFixed(2)}조`; // Trillion KRW
            } else {
                return `$${(cap / 1e9).toFixed(2)}B`; // Billion USD
            }
        };

        const formatPrice = (price) => {
            if (currency === 'KRW') {
                return `₩${price.toLocaleString()}`;
            } else {
                return `$${price}`;
            }
        };

        return [{
            type: 'treemap',
            labels: labels,
            parents: parents,
            values: values,
            text: customText,
            textposition: 'middle center',
            hovertemplate: '<b>%{label}</b><br>' +
                `Price: ${currency === 'KRW' ? '₩' : '$'}%{customdata[0]}<br>` +
                'Change: %{customdata[1]:.2f}%<br>' +
                'Market Cap: %{customdata[2]}<br>' +
                '<extra></extra>',
            customdata: data.map(d => [
                currency === 'KRW' ? d.price.toLocaleString() : d.price,
                d.change,
                formatMarketCap(d.marketCap)
            ]),
            marker: {
                colors: changes,
                colorscale: [
                    [0, '#dc2626'],      // Red (deep loss)
                    [0.4, '#ef4444'],    // Light red
                    [0.5, '#6b7280'],    // Gray (neutral)
                    [0.6, '#22c55e'],    // Light green
                    [1, '#16a34a']       // Green (strong gain)
                ],
                cmid: 0,
                colorbar: {
                    title: 'Change %',
                    thickness: 15,
                    len: 0.7,
                    tickfont: { color: '#cbd5e1' },
                    titlefont: { color: '#cbd5e1' }
                },
                line: {
                    color: activeStatus.map(isActive => isActive ? '#ffffff' : 'rgba(255,255,255,0.1)'),
                    width: activeStatus.map(isActive => isActive ? 3 : 0.5)
                }
            },
            textfont: {
                color: '#ffffff',
                size: 12,
                family: 'Inter, sans-serif'
            }
        }];
    };

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { l: 5, r: 5, t: 5, b: 5 },
        height: 400,
        font: { color: '#cbd5e1' }
    };

    return (
        <div className="glass-panel" style={{ padding: '15px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Grid3x3 size={18} color="var(--accent-color)" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>
                        {selectedMarket === 'kr' ? 'KOSPI' : 'NASDAQ'} Market Map
                    </h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        (⭐ = Live Data Available)
                    </span>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {lastUpdated && <span>Updated: {lastUpdated.toLocaleTimeString()}</span>}
                    <button onClick={() => fetchData(selectedMarket)} className="icon-button" style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                        <RefreshCw size={14} className={loading ? 'spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Market Switcher Tabs */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                <button
                    onClick={() => handleMarketSwitch('kr')}
                    style={{
                        padding: '8px 16px',
                        background: selectedMarket === 'kr' ? 'var(--accent-color)' : 'rgba(255,255,255,0.05)',
                        border: selectedMarket === 'kr' ? '1px solid var(--accent-color)' : '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        fontWeight: selectedMarket === 'kr' ? '600' : '400',
                        transition: 'all 0.2s ease'
                    }}
                >
                    🇰🇷 KOSPI
                </button>
                <button
                    onClick={() => handleMarketSwitch('us')}
                    style={{
                        padding: '8px 16px',
                        background: selectedMarket === 'us' ? 'var(--accent-color)' : 'rgba(255,255,255,0.05)',
                        border: selectedMarket === 'us' ? '1px solid var(--accent-color)' : '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        fontWeight: selectedMarket === 'us' ? '600' : '400',
                        transition: 'all 0.2s ease'
                    }}
                >
                    🇺🇸 NASDAQ
                </button>
            </div>

            {/* Treemap */}
            <div style={{ position: 'relative', minHeight: '400px' }}>
                {error && (
                    <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--danger-color)' }}>
                        Failed to load market map: {error}
                    </div>
                )}
                {data.length > 0 ? (
                    <Plot
                        data={plotData()}
                        layout={layout}
                        config={{ responsive: true, displayModeBar: false }}
                        style={{ width: '100%', height: '100%' }}
                        onClick={(event) => {
                            if (event.points && event.points.length > 0 && onSymbolClick) {
                                const symbol = event.points[0].label;
                                // For KR stocks, pass the clean symbol without .KS
                                onSymbolClick(symbol);
                            }
                        }}
                    />
                ) : (
                    !loading && !error && (
                        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--text-secondary)' }}>
                            Loading market data...
                        </div>
                    )
                )}
            </div>
        </div>
    );
};

export default MarketMap;
