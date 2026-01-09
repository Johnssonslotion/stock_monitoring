import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';

/**
 * 실시간 체결 가시화 패널
 * @param {Array} initialData 초기 로드된 틱 데이터
 * @param {Object} realTimeData 웹소켓으로 들어온 최신 틱
 */
const TickerPanel = ({ initialData = [], realTimeData }) => {
    const [ticks, setTicks] = useState([]);

    useEffect(() => {
        if (initialData.length > 0) {
            setTicks(initialData);
        }
    }, [initialData]);

    useEffect(() => {
        if (realTimeData && realTimeData.type === 'ticker') {
            setTicks(prev => [realTimeData, ...prev].slice(0, 50));
        }
    }, [realTimeData]);

    return (
        <div className="glass-panel animate-fade-in" style={{ height: '400px', overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                <Activity size={20} color="#58a6ff" style={{ marginRight: '10px' }} />
                <h3 style={{ margin: 0 }}>Real-time Trades</h3>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textAlign: 'left' }}>
                        <th style={{ padding: '8px' }}>Time</th>
                        <th style={{ padding: '8px' }}>Symbol</th>
                        <th style={{ padding: '8px' }}>Price</th>
                        <th style={{ padding: '8px' }}>Change</th>
                    </tr>
                </thead>
                <tbody>
                    {ticks.map((tick, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-color)', fontSize: '0.9rem' }}>
                            <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>
                                {new Date(tick.timestamp).toLocaleTimeString()}
                            </td>
                            <td style={{ padding: '8px', fontWeight: 'bold' }}>{tick.symbol}</td>
                            <td style={{ padding: '8px', color: tick.change >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
                                {tick.price.toLocaleString()}
                            </td>
                            <td style={{ padding: '8px', display: 'flex', alignItems: 'center' }}>
                                {tick.change >= 0 ? <TrendingUp size={14} style={{ marginRight: '4px' }} /> : <TrendingDown size={14} style={{ marginRight: '4px' }} />}
                                {tick.change}%
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default TickerPanel;
