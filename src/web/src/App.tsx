import React, { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { fetchJson } from './api';
import { LayoutDashboard, Map as MapIcon, Activity, Settings, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { CandleChart } from './components/CandleChart';
import { LogsView } from './components/LogsView';
import { MarketMap } from './components/MarketMap';
// import { StatusPanel } from './components/StatusPanel'; // Deprecated
import { SystemDashboard } from './components/SystemDashboard';
import { SymbolSelector } from './components/SymbolSelector';
import { TimeframeSelector, type Timeframe } from './components/TimeframeSelector';
import { ServerStatus } from './components/ServerStatus';
import { TradingPanel } from './components/TradingPanel';
import { TickerTape } from './components/TickerTape';
// import { MarketInfoPanel } from './components/MarketInfoPanel'; // Refactored into TradingPanel
import { generateMockCandles } from './mocks/tradingMocks';
import { isMarketOpen } from './mocks/marketHoursMock';


/* 
  Data interfaces
*/
interface CandleData {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

function App() {
  // Global State
  const [activeTab, setActiveTab] = useState<'dashboard' | 'analysis' | 'system'>('dashboard');
  const [selectedSymbol, setSelectedSymbol] = useState('005930'); // Default: Samsung Electronics
  const [selectedName, setSelectedName] = useState('삼성전자');
  // Dashboard Data State
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [selectedInterval, setSelectedInterval] = useState<Timeframe>('1d');
  const [isLoading, setIsLoading] = useState(true); // Loading state (Default true for smooth transition)
  const [dataSource, setDataSource] = useState<'real' | 'mock' | 'partial'>('mock'); // Track data source
  const [dataGaps, setDataGaps] = useState<{ count: number, maxGapHours: number }>({ count: 0, maxGapHours: 0 }); // Track time gaps
  const [marketOpen, setMarketOpen] = useState<boolean>(true); // Track if market is currently open

  // URL Synchronization
  useEffect(() => {
    // 1. Read URL on mount
    const params = new URLSearchParams(window.location.search);
    const symbolParam = params.get('selected');
    if (symbolParam && symbolParam !== selectedSymbol) {
      console.log(`🔗 URL Sync: Loading symbol from URL: ${symbolParam}`);
      setSelectedSymbol(symbolParam);
      setActiveTab('analysis'); // If symbol is present in URL, go to analysis view

      // Fetch symbol name from market-map API
      fetchJson<any>('/market-map/kr').then(data => {
        if (!data) return;
        const items = data.symbols || [];
        const found = items.find((item: any) => item.symbol === symbolParam);
        if (found) {
          setSelectedName(found.name);
          console.log(`🔗 URL Sync: Loaded name: ${found.name}`);
        }
      }).catch(err => {
        console.warn('Failed to fetch symbol name:', err);
      });
    }
  }, []);

  useEffect(() => {
    // 2. Write URL on change
    const url = new URL(window.location.href);
    if (selectedSymbol) {
      url.searchParams.set('selected', selectedSymbol);
      window.history.replaceState({}, '', url);
    }
  }, [selectedSymbol]);

  // Electron IPC Listener
  useEffect(() => {
    if (window.ipcRenderer) {
      console.log("🚀 Running in Electron environment");
      window.ipcRenderer.on('main-process-message', (_event, message) => {
        console.log("📩 [Main Process]:", message);
      });
    }
  }, []);

  // Fetch Candles when symbol changes (Only if on analysis)
  // Fetch Candles when symbol changes (Only if on analysis)
  useEffect(() => {
    if (activeTab === 'analysis') {
      const fetchCandles = async () => {
        try {
          setIsLoading(true);
          console.log(`🔄 Fetching candles: symbol=${selectedSymbol}, interval=${selectedInterval}, limit=5000`);

          // Update market status
          const market = selectedSymbol.startsWith('0') ? 'kr' : 'us';
          setMarketOpen(isMarketOpen(market));

          // Using fetchJson wrapper (Phase 14)
          // Base URL is triggered at /api/v1/candles/...
          const data = await fetchJson<any[]>(`/candles/${selectedSymbol}?limit=5000&interval=${selectedInterval}`);

          if (data && data.length > 0) {
            console.log(`✅ Received ${data.length} candles for ${selectedSymbol} @ ${selectedInterval}`);
            // Transform if necessary (API returns ISO string time, Frontend expects it compatible)
            // Frontend CandleData defines time as string | number.
            // API uses ISO string? Or milliseconds?
            // backend `get_recent_candles` uses standard dict(row).
            // If DB stores time as timestamp, it likely returns ISO string in JSON.
            // CandleChart handles `new Date(d.time).getTime() / 1000`.
            // Wait, `CandleChart` does NOT handle conversion inside the component currently,
            // it expects `CandleData` passed in props.
            // We need to map it here to match `CandleData[].time`.

            // Check what MOCK data looks like.
            // MOCK_CANDLES has `time` as Unix Timestamp (Numbers) usually for lightweight-charts.
            // Let's ensure compatibility.
            const formattedData = data.map((d: any) => {
              // Try to detect if time is string or number
              let t = d.time;
              if (typeof t === 'string') {
                // Convert ISO to Unix param (seconds) for lightweight-charts
                t = new Date(t).getTime() / 1000;
              }
              return {
                time: t,
                open: d.open,
                high: d.high,
                low: d.low,
                close: d.close,
                volume: d.volume
              };
            }).sort((a: any, b: any) => a.time - b.time);

            // Temporal Gap Detection (시간적 연속성 검증)
            const intervalSeconds: Record<string, number> = { '1m': 60, '5m': 300, '1d': 86400 };
            const expectedGap = intervalSeconds[selectedInterval] || 86400;
            const maxAllowedGap = expectedGap * 3; // Allow up to 3x the expected interval

            let gapCount = 0;
            let maxGapHours = 0;

            for (let i = 1; i < formattedData.length; i++) {
              const prevTime = formattedData[i - 1].time as number;
              const currTime = formattedData[i].time as number;
              const gap = currTime - prevTime;

              if (gap > maxAllowedGap) {
                gapCount++;
                const gapHours = gap / 3600;
                if (gapHours > maxGapHours) {
                  maxGapHours = gapHours;
                }
              }
            }

            setDataGaps({ count: gapCount, maxGapHours: Math.round(maxGapHours * 10) / 10 });

            // Check data quality
            const expectedMinimum = 50; // Expect at least 50 candles for good quality
            if (formattedData.length < expectedMinimum) {
              setDataSource('partial'); // Partial data warning
              console.warn(`⚠️ Partial data: received ${formattedData.length} / expected ${expectedMinimum}+`);
            } else if (gapCount > 0) {
              setDataSource('partial'); // Gaps detected
              console.warn(`⚠️ Data gaps detected: ${gapCount} gap(s), max gap: ${maxGapHours.toFixed(1)}h`);
            } else {
              setDataSource('real'); // Good quality real data
            }

            setCandles(formattedData);
          } else {
            throw new Error("Empty API Response");
          }

        } catch (error) {
          console.warn("⚠️ API Unavailable or Empty, falling back to MOCK data");
          setDataSource('mock'); // Mark as mock data
          setDataGaps({ count: 0, maxGapHours: 0 }); // Reset gaps
          // Generate appropriate mock data based on interval
          let intervalSeconds = 86400; // Default 1d
          if (selectedInterval === '1m') intervalSeconds = 60;
          else if (selectedInterval === '5m') intervalSeconds = 300;

          // Generate 200 candles to fill the chart
          // Use a deterministic start price for 'Samsung' (simulated)
          const mockPrice = selectedSymbol === '005930' ? 70000 : 150000;
          const fallbackData = generateMockCandles(200, mockPrice, intervalSeconds);

          setCandles(fallbackData);
        } finally {
          setIsLoading(false);
        }
      };

      fetchCandles();
      // Optional: Poll candles every minute
      const interval = setInterval(fetchCandles, 60000);
      return () => clearInterval(interval);
    }
  }, [selectedSymbol, activeTab, selectedInterval]);

  return (
    <div className="flex h-screen bg-[#050505] text-gray-100 font-sans overflow-hidden bg-[url('https://grainy-gradients.vercel.app/noise.svg')] bg-opacity-20">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/10 via-transparent to-purple-900/10 pointer-events-none" />

      {/* Sidebar Navigation */}
      <div className="w-20 z-20 flex flex-col items-center glass border-r-0 border-r-white/5 py-6 gap-8 m-2 rounded-2xl">
        <div className="mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">
            A
          </div>
        </div>

        <NavButton
          active={activeTab === 'dashboard'}
          onClick={() => setActiveTab('dashboard')}
          icon={<MapIcon />}
          label="Map"
        />
        <NavButton
          active={activeTab === 'analysis'}
          onClick={() => setActiveTab('analysis')}
          icon={<LayoutDashboard />}
          label="Analyze"
        />
        <NavButton
          active={activeTab === 'system'}
          onClick={() => setActiveTab('system')}
          icon={<Settings />}
          label="System"
        />

        <div className="mt-auto">
          <NavButton icon={<Settings />} label="Set" />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden relative z-10 p-6">
        {/* Data Quality Warning Badge */}
        <AnimatePresence>
          {dataSource !== 'real' && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={clsx(
                "mb-4 px-4 py-2 rounded-lg border flex items-center gap-3",
                dataSource === 'mock' && "bg-amber-500/10 border-amber-500/30 text-amber-400",
                dataSource === 'partial' && "bg-orange-500/10 border-orange-500/30 text-orange-400"
              )}
            >
              <span className="text-xl">⚠️</span>
              <div className="flex-1">
                <div className="font-semibold">
                  {dataSource === 'mock' && (marketOpen ? 'Mock Data Mode' : 'Market Closed (Simulation)')}
                  {dataSource === 'partial' && (
                    dataGaps.count > 0 ? `Data Gaps Detected (${dataGaps.count})` : 'Partial Data Warning'
                  )}
                </div>
                <div className="text-sm opacity-80">
                  {dataSource === 'mock' && (
                    marketOpen
                      ? 'Backend API unavailable. Displaying simulated data for demonstration.'
                      : 'Market is currently closed. Showing historical simulation data.'
                  )}
                  {dataSource === 'partial' && dataGaps.count > 0 && (
                    `실제 데이터이나 시간적 누락 발견: ${dataGaps.count}개 구간, 최대 갭 ${dataGaps.maxGapHours}시간`
                  )}
                  {dataSource === 'partial' && dataGaps.count === 0 && (
                    'Incomplete data received from backend. Some candles may be missing.'
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Top Header (Contextual) */}
        <header className="h-14 glass rounded-xl mb-2 flex items-center px-6 justify-between shrink-0 relative z-50">
          <h1 className="text-lg font-bold flex items-center gap-3 text-white tracking-tight">
            <span className="w-1.5 h-6 bg-blue-500 rounded-full inline-block" />
            {activeTab === 'dashboard' && 'Market Map Overview'}
            {activeTab === 'analysis' && 'Professional analysis'}
            {activeTab === 'system' && 'System Health'}
          </h1>

          {/* Controls */}
          {activeTab === 'analysis' && (
            <div className="flex items-center gap-4 bg-black/20 p-1 pl-4 rounded-lg border border-white/5">
              <ServerStatus />
              <div className="w-px h-6 bg-white/10 mx-2" />
              {/* Date Navigator Placeholder */}
              <div className="flex items-center gap-2 bg-white/5 px-2 py-1 rounded border border-white/10">
                <span className="text-[10px] text-gray-500 uppercase tracking-tighter">Date</span>
                <input type="date" className="bg-transparent text-xs text-blue-400 outline-none border-none [color-scheme:dark]" defaultValue="2026-01-15" />
              </div>
              <div className="w-px h-6 bg-white/10 mx-2" />
              <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">Asset</span>
              <SymbolSelector
                currentSymbol={selectedSymbol}
                onChange={(symbol, name) => {
                  setSelectedSymbol(symbol);
                  setSelectedName(name);
                }}
              />
              <div className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white cursor-pointer">
                <Search size={16} />
              </div>
            </div>
          )}
        </header>

        {/* Ticker Tape */}
        <TickerTape />

        {/* Tab Content with Animation */}
        <main className="flex-1 overflow-hidden relative rounded-xl mt-1">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 5, scale: 0.995 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -5, scale: 0.995 }}
              transition={{ duration: 0.1, ease: "easeOut" }}
              className="absolute inset-0"
            >
              {activeTab === 'dashboard' && (
                <div className="w-full h-full glass rounded-xl overflow-hidden shadow-xl flex flex-col relative p-1">
                  <div className="px-4 py-2 border-b border-white/5 bg-white/5 flex justify-between items-center shrink-0">
                    <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Market Map Overview</span>
                  </div>
                  <MarketMap
                    filterType="STOCK"
                    onSymbolClick={(symbol: string, name: string) => {
                      setSelectedSymbol(symbol);
                      setSelectedName(name);
                      setActiveTab('analysis'); // Auto switch to analysis
                    }}
                  />
                </div>
              )}

              {activeTab === 'analysis' && (
                <div className="w-full h-full flex gap-2 p-1">
                  {/* Left Section: Professional Chart (75%) */}
                  <div className="flex-[7.5] flex flex-col gap-2 min-w-0 min-h-0">
                    <div
                      data-testid="chart-section"
                      className="flex-1 flex flex-col glass rounded-xl overflow-hidden shadow-2xl relative min-h-0"
                    >
                      {/* Chart Info Overlay */}
                      <div className="absolute top-3 left-4 z-10 flex items-center gap-2 pointer-events-none">
                        <span className="px-2 py-0.5 bg-blue-600/80 text-[10px] font-bold rounded-sm uppercase tracking-tighter shadow-lg shadow-blue-500/20 backdrop-blur-md">
                          {selectedName} ({selectedSymbol})
                        </span>
                        <div className="flex gap-2">
                          <div className="flex gap-1 bg-black/40 px-2 py-0.5 rounded-sm backdrop-blur-sm border border-white/5">
                            <span className="text-[10px] text-gray-400 font-medium uppercase">ANALYSIS</span>
                            <div className="w-px h-3 bg-white/10 mx-0.5" />
                            <span className="text-[10px] text-green-400 font-bold">LIVE</span>
                          </div>
                          <div className={clsx(
                            "flex items-center gap-1 px-2 py-0.5 rounded-sm backdrop-blur-sm border",
                            import.meta.env.DEV
                              ? "bg-purple-500/20 border-purple-500/30 text-purple-300"
                              : "bg-blue-500/20 border-blue-500/30 text-blue-300"
                          )}>
                            <span className="text-[10px] font-bold">
                              {import.meta.env.DEV ? 'LOCAL API' : 'SERVER API'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Chart Controls Group (Timeframe + Zoom) */}
                      <div className="absolute top-3 right-16 z-10 flex items-center gap-2">
                        <TimeframeSelector selected={selectedInterval} onChange={setSelectedInterval} />
                        <div className="flex gap-1">
                          <button onClick={() => {
                            const chart = (document.querySelector('.candlechart-container') as any)?.__chartInstance;
                            if (chart) {
                              const timeScale = chart.timeScale();
                              const currentRange = timeScale.getVisibleLogicalRange();
                              if (currentRange) {
                                const range = currentRange.to - currentRange.from;
                                const delta = range * 0.2;
                                timeScale.setVisibleLogicalRange({ from: currentRange.from + delta, to: currentRange.to });
                              }
                            }
                          }} className="p-1.5 bg-gray-800/80 hover:bg-gray-700 text-white rounded border border-white/10 shadow-lg" title="Zoom In">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                          </button>
                          <button onClick={() => {
                            const chart = (document.querySelector('.candlechart-container') as any)?.__chartInstance;
                            if (chart) {
                              const timeScale = chart.timeScale();
                              const currentRange = timeScale.getVisibleLogicalRange();
                              if (currentRange) {
                                const range = currentRange.to - currentRange.from;
                                const delta = range * 0.2;
                                timeScale.setVisibleLogicalRange({ from: currentRange.from - delta, to: currentRange.to });
                              }
                            }
                          }} className="p-1.5 bg-gray-800/80 hover:bg-gray-700 text-white rounded border border-white/10 shadow-lg" title="Zoom Out">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                          </button>
                          <button onClick={() => {
                            const chart = (document.querySelector('.candlechart-container') as any)?.__chartInstance;
                            if (chart) chart.timeScale().fitContent();
                          }} className="p-1.5 bg-gray-800/80 hover:bg-gray-700 text-white rounded border border-white/10 shadow-lg" title="Reset Zoom">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
                          </button>
                        </div>
                      </div>

                      {/* Loading Indicator Overlay */}
                      <AnimatePresence>
                        {isLoading && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.15 }}
                            className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm z-20"
                          >
                            <div className="flex flex-col items-center gap-3">
                              <div className="relative w-12 h-12 text-blue-500">
                                <Activity size={48} className="animate-pulse" />
                              </div>
                              <span className="text-xs text-gray-300 font-medium tracking-wide">
                                Syncing {selectedInterval.toUpperCase()} Market Data...
                              </span>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <CandleChart data={candles} symbol={selectedSymbol} interval={selectedInterval} />
                    </div>
                  </div>

                  {/* Right Section: Order Book & Executions (2.5%) */}
                  {/* Right Section: Trading Panel & Info (25% -> 20% visual) */}
                  <div className="flex-[2.5] flex flex-col gap-2 min-w-0 min-h-0">

                    {/* Advanced Trading Panel (OrderBook + Histo + MarketInfo) */}
                    <div className="flex-1 min-h-0">
                      <TradingPanel symbol={selectedSymbol} />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'system' && (
                <div className="w-full h-full flex flex-col gap-2">
                  {/* System Dashboard */}
                  <div className="flex-[4] flex items-center justify-center">
                    <SystemDashboard />
                  </div>
                  {/* System Logs */}
                  <div className="flex-[6] glass rounded-xl overflow-hidden p-2">
                    <div className="px-3 py-2 bg-gray-800/50 border-b border-white/5 mb-2">
                      <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">System Monitoring (All Symbols)</span>
                    </div>
                    <LogsView />
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div >
  );
}

// Sub-component for Nav Button with Glow
const NavButton = ({ active, onClick, icon, label }: any) => (
  <button
    onClick={onClick}
    className={clsx(
      "group flex flex-col items-center justify-center w-14 h-14 rounded-2xl transition-all duration-300 relative",
      active
        ? "glass-active"
        : "text-gray-500 hover:text-gray-200 hover:bg-white/5"
    )}
  >
    {active && (
      <motion.div
        layoutId="nav-glow"
        className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full"
        transition={{ duration: 0.3 }}
      />
    )}
    <div className="relative z-10 flex flex-col items-center">
      {React.cloneElement(icon, { size: 22, strokeWidth: active ? 2.5 : 2 })}
      <span className={clsx("text-[9px] mt-1.5 font-medium tracking-wide transition-colors", active ? "text-blue-100" : "group-hover:text-white")}>
        {label}
      </span>
    </div>
  </button>
);

export default App;
