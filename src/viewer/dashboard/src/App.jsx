import React, { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useApi } from './hooks/useApi';
import TickerPanel from './components/TickerPanel';
import OrderbookChart from './components/OrderbookChart';
import { Shield, Radio, Server, Monitor } from 'lucide-react';
import './index.css';

// API 서버 URL 구성 (환경변수 우선, 포트포워딩 및 원격 접속 모두 지원)
// SSH 포트포워딩 사용 시: localhost:5173에서 접속하므로 localhost:8000 사용
// 원격 직접 접속 시: 서버IP:5173에서 접속하므로 서버IP:8000 사용
const API_HOST = import.meta.env.VITE_API_HOST || window.location.hostname;
const API_PORT = import.meta.env.VITE_API_PORT || '8000';
const API_SERVER = `http://${API_HOST}:${API_PORT}`;
const WS_SERVER = `ws://${API_HOST}:${API_PORT}/ws`;

console.log('🔧 API Configuration:', { API_HOST, API_PORT, API_SERVER, WS_SERVER });

function App() {
  const { data: realTimeData, status: wsStatus } = useWebSocket(WS_SERVER);
  const { request } = useApi(API_SERVER);
  const [initialTicks, setInitialTicks] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('005930'); // 삼성전자 종목코드

  // 초기 틱 데이터 로드 (Gate 2 검증용)
  useEffect(() => {
    const fetchInitialData = async () => {
      const data = await request(`/api/v1/ticks/${selectedSymbol}`);
      if (data) setInitialTicks(data);
    };
    fetchInitialData();
  }, [request, selectedSymbol]);

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

      {/* Main Dashboard Grid */}
      <main style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 1fr) 2fr', gap: '25px' }}>
        {/* Left Column: Trades */}
        <TickerPanel initialData={initialTicks} realTimeData={realTimeData} />

        {/* Right Column: Orderbook Visualization */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
          <OrderbookChart realTimeData={realTimeData} />

          <div className="glass-panel" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
            <p>Analytics Engine Waiting for Data Streams...</p>
          </div>
        </div>
      </main>

      <footer style={{ marginTop: '40px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
        &copy; 2026 Antigravity - Premium Investing Infrastructure
      </footer>
    </div>
  );
}

export default App;
