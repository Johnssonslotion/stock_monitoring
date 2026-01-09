import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { Layers } from 'lucide-react';

/**
 * 실시간 호가 잔량 시각화 컴포넌트
 * @param {Object} realTimeData 웹소켓으로 들어온 최신 호가 스냅샷
 */
const OrderbookChart = ({ realTimeData }) => {
    const [data, setData] = useState(null);

    useEffect(() => {
        if (realTimeData && realTimeData.type === 'orderbook') {
            const asks = realTimeData.asks.sort((a, b) => b.price - a.price); // 높은 가격 상단
            const bids = realTimeData.bids.sort((a, b) => b.price - a.price); // 높은 가격 상단

            const plotData = [
                {
                    x: asks.map(a => a.vol),
                    y: asks.map(a => a.price),
                    type: 'bar',
                    orientation: 'h',
                    name: 'Asks',
                    marker: { color: 'rgba(248, 81, 73, 0.6)' },
                },
                {
                    x: bids.map(b => b.vol),
                    y: bids.map(b => b.price),
                    type: 'bar',
                    orientation: 'h',
                    name: 'Bids',
                    marker: { color: 'rgba(63, 185, 80, 0.6)' },
                }
            ];
            setData(plotData);
        }
    }, [realTimeData]);

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#8b949e', size: 10 },
        showlegend: false,
        margin: { l: 60, r: 20, t: 10, b: 30 },
        xaxis: { gridcolor: 'rgba(48, 54, 61, 0.2)', zeroline: false },
        yaxis: { gridcolor: 'rgba(48, 54, 61, 0.2)', zeroline: false },
        height: 350,
        autosize: true
    };

    return (
        <div className="glass-panel animate-fade-in" style={{ gridColumn: 'span 2' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                <Layers size={20} color="#bc8cff" style={{ marginRight: '10px' }} />
                <h3 style={{ margin: 0 }}>Orderbook Depth (Top 5)</h3>
            </div>

            {data ? (
                <Plot
                    data={data}
                    layout={layout}
                    config={{ displayModeBar: false, responsive: true }}
                    style={{ width: '100%' }}
                />
            ) : (
                <div style={{ height: '350px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                    Waiting for orderbook data...
                </div>
            )}
        </div>
    );
};

export default OrderbookChart;
