import React, { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useApi } from './hooks/useApi';
import TickerPanel from './components/TickerPanel';
import OrderbookChart from './components/OrderbookChart';
import CandleChart from './components/CandleChart';
import MarketMap from './components/MarketMap';
import { Shield, Radio, Server, Monitor } from 'lucide-react';
import { WS_SERVER, API_SERVER } from './config';
import './index.css';

function App() {
  const { data: realTimeData, status: wsStatus } = useWebSocket(WS_SERVER);
  const { request } = useApi(API_SERVER);
  const [initialTicks, setInitialTicks] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('QQQ'); // QQQ 데이터 available

  // 초기 틱 데이터 로드 (Gate 2 검증용)
  useEffect(() => {
    const fetchInitialData = async () => {
      const data = await request(`/api/v1/ticks/${selectedSymbol}`);
      if (data) setInitialTicks(data);
    };
    fetchInitialData();
  }, [request, selectedSymbol]);

  // Symbol click handler from MarketMap
  const handleSymbolClick = (symbol) => {
    console.log('Switching to symbol:', symbol);
    setSelectedSymbol(symbol);
  };

  return (
    <div style={{ padding: '30px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header Area */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Monitor size={32} color="#58a6ff" style={{ marginRight: '15px' }} />
          <div>
            <h1 style={{ margin: 0, fontSize: '1.8rem' }}>Antigravity Terminal</h1>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Real-time Market Monitoring</p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '15px' }}>
          <div className="glass-panel" style={{ padding: '8px 15px', display: 'flex', alignItems: 'center', fontSize: '0.85rem' }}>
            <Radio size={14} color={wsStatus === 'connected' ? 'var(--success-color)' : 'var(--danger-color)'} style={{ marginRight: '8px' }} />
            WS: {wsStatus.toUpperCase()}
          </div>
          <div className="glass-panel" style={{ padding: '8px 15px', display: 'flex', alignItems: 'center', fontSize: '0.85rem' }}>
            <Server size={14} color="var(--accent-color)" style={{ marginRight: '8px' }} />
            API: ONLINE
          </div>
          <div className="glass-panel" style={{ padding: '8px 15px', display: 'flex', alignItems: 'center', fontSize: '0.85rem' }}>
            <Shield size={14} color="var(--success-color)" style={{ marginRight: '8px' }} />
            SECURED
          </div>
        </div>
      </header>

      {/* Market Map (Full Width) */}
      <MarketMap onSymbolClick={handleSymbolClick} />

      {/* Main Dashboard Grid */}
      <main style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 1fr) 2fr', gap: '25px', marginTop: '25px' }}>
        {/* Left Column: Trades */}
        <TickerPanel initialData={initialTicks} realTimeData={realTimeData} />

        {/* Right Column: Orderbook Visualization & Chart */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
          <OrderbookChart realTimeData={realTimeData} />

          <CandleChart symbol={selectedSymbol} />
        </div>
      </main>

      <footer style={{ marginTop: '40px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
        &copy; 2026 Antigravity - Premium Investing Infrastructure
      </footer>
    </div>
  );
}

export default App;
