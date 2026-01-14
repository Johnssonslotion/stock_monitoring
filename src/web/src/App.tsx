import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { clsx } from 'clsx';
import { LayoutDashboard, Map as MapIcon, List, Activity, Settings, Search, TrendingUp as TrendingUpIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { CandleChart } from './components/CandleChart';
import { LogsView } from './components/LogsView';
import { MarketMap } from './components/MarketMap';
// import { StatusPanel } from './components/StatusPanel'; // Deprecated
import { SystemDashboard } from './components/SystemDashboard';
import { SymbolSelector } from './components/SymbolSelector';
import { SectorPerformance } from './components/SectorPerformance';
import { TimeframeSelector, type Timeframe } from './components/TimeframeSelector';


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
  const [activeTab, setActiveTab] = useState<'dashboard' | 'map' | 'logs' | 'system'>('dashboard');
  const [selectedSymbol, setSelectedSymbol] = useState('005930'); // Default: Samsung Electronics
  const [selectedName, setSelectedName] = useState('삼성전자');
  // Dashboard Data State
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [selectedInterval, setSelectedInterval] = useState<Timeframe>('1d');
  const [isMapExpanded, setIsMapExpanded] = useState(true); // Map-First 초기값
  const [isLoading, setIsLoading] = useState(false); // Loading state

  // Electron IPC Listener
  useEffect(() => {
    if (window.ipcRenderer) {
      console.log("🚀 Running in Electron environment");
      window.ipcRenderer.on('main-process-message', (_event, message) => {
        console.log("📩 [Main Process]:", message);
      });
    }
  }, []);

  // Fetch Candles when symbol changes (Only if on dashboard)
  useEffect(() => {
    if (activeTab === 'dashboard') {
      const fetchCandles = async () => {
        try {
          setIsLoading(true);
          console.log(`🔄 Fetching candles: symbol=${selectedSymbol}, interval=${selectedInterval}, limit=5000`);
          const response = await axios.get(`/candles/${selectedSymbol}`, {
            params: {
              limit: 5000,
              interval: selectedInterval
            }
          });
          console.log(`✅ Received ${response.data.length} candles for ${selectedSymbol} @ ${selectedInterval}`);
          setCandles(response.data);
        } catch (error) {
          console.error("❌ Failed to fetch candles:", error);
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
          icon={<LayoutDashboard />}
          label="Dash"
        />
        <NavButton
          active={activeTab === 'map'}
          onClick={() => setActiveTab('map')}
          icon={<MapIcon />}
          label="Map"
        />
        <NavButton
          active={activeTab === 'logs'}
          onClick={() => setActiveTab('logs')}
          icon={<List />}
          label="Logs"
        />
        <NavButton
          active={activeTab === 'system'}
          onClick={() => setActiveTab('system')}
          icon={<Activity />}
          label="System"
        />

        <div className="mt-auto">
          <NavButton icon={<Settings />} label="Set" />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden relative z-10 p-2 pl-0">
        {/* Top Header (Contextual) */}
        <header className="h-14 glass rounded-xl mb-2 flex items-center px-6 justify-between shrink-0 relative z-50">
          <h1 className="text-lg font-bold flex items-center gap-3 text-white tracking-tight">
            <span className="w-1.5 h-6 bg-blue-500 rounded-full inline-block" />
            {activeTab === 'dashboard' && 'Market Dashboard'}
            {activeTab === 'map' && 'Market Map (KOSPI)'}
            {activeTab === 'logs' && 'Data Ingestion Logs'}
            {activeTab === 'system' && 'System Health'}
          </h1>

          {/* Controls */}
          {activeTab === 'dashboard' && (
            <div className="flex items-center gap-4 bg-black/20 p-1 pl-4 rounded-lg border border-white/5">
              <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">Asset</span>
              <SymbolSelector
                currentSymbol={selectedSymbol}
                onChange={(symbol, name) => {
                  setSelectedSymbol(symbol);
                  setSelectedName(name);
                  setIsMapExpanded(false); // 종목 클릭 시 차트 확장
                }}
              />
              <div className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white cursor-pointer">
                <Search size={16} />
              </div>
            </div>
          )}
        </header>

        {/* Tab Content with Animation */}
        <main className="flex-1 overflow-hidden relative rounded-xl">
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
                <div className="w-full h-full flex gap-2 p-1">
                  {/* Left Section: Market Map (70% or 30%) */}
                  <motion.div
                    animate={{ flex: isMapExpanded ? 7 : 3 }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    className="glass rounded-xl overflow-hidden shadow-xl flex flex-col relative"
                  >
                    <div className="px-4 py-2 border-b border-white/5 bg-white/5 flex justify-between items-center shrink-0">
                      <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Market Map Overview</span>
                      <button
                        onClick={() => setIsMapExpanded(!isMapExpanded)}
                        className="text-[10px] bg-white/5 hover:bg-white/10 px-2 py-0.5 rounded text-gray-400"
                      >
                        {isMapExpanded ? 'Collapse' : 'Expand'}
                      </button>
                    </div>
                    <div className="flex-1 min-h-0">
                      <MarketMap
                        filterType="STOCK"
                        onSymbolClick={(symbol: string, name: string) => {
                          setSelectedSymbol(symbol);
                          setSelectedName(name);
                          setIsMapExpanded(false); // 종목 클릭 시 차트 확장
                        }}
                      />
                    </div>
                  </motion.div>

                  {/* Right Section: Focus (Chart + Ticks) (30% or 70%) */}
                  <motion.div
                    animate={{ flex: isMapExpanded ? 3 : 7 }}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    className="flex flex-col gap-2 min-w-0"
                  >
                    {/* Top: Chart */}
                    <div className="flex-[6] glass rounded-xl overflow-hidden shadow-2xl relative">
                      {/* Chart Info Overlay */}
                      <div className="absolute top-3 left-4 z-10 flex items-center gap-2 pointer-events-none">
                        <span className="px-2 py-0.5 bg-blue-600/80 text-[10px] font-bold rounded-sm uppercase tracking-tighter shadow-lg shadow-blue-500/20 backdrop-blur-md">
                          {selectedName} ({selectedSymbol})
                        </span>
                        <span className="hidden sm:inline-block text-[10px] text-gray-400 font-medium bg-black/40 px-2 py-0.5 rounded-sm backdrop-blur-sm border border-white/5">
                          {isMapExpanded ? 'PREVIEW' : 'ANALYSIS'}
                        </span>
                      </div>

                      {/* Timeframe Selector */}
                      <div className="absolute top-3 right-4 z-10">
                        <TimeframeSelector selected={selectedInterval} onChange={setSelectedInterval} />
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
                              <div className="relative w-12 h-12">
                                {/* Outer Ring */}
                                <div className="absolute inset-0 rounded-full border-2 border-blue-500/20"></div>
                                {/* Spinning Ring */}
                                <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 border-r-blue-500 animate-spin"></div>
                                {/* Inner Glow */}
                                <div className="absolute inset-2 bg-blue-500/20 rounded-full blur-md"></div>
                              </div>
                              <span className="text-xs text-gray-300 font-medium tracking-wide">
                                Loading {selectedInterval.toUpperCase()} Data...
                              </span>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <CandleChart data={candles} symbol={selectedSymbol} interval={selectedInterval} />
                    </div>

                    {/* Bottom: Ticks (Only visible or relevant when focused) */}
                    <div className="flex-[4] glass rounded-xl overflow-hidden flex flex-col shadow-xl">
                      <div className="px-4 py-2 border-b border-white/5 bg-white/5 flex justify-between items-center shrink-0">
                        <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Live Execution</span>
                        <div className="flex gap-1.5 items-center">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                          <span className="text-[10px] text-green-400 font-mono">STREAMS</span>
                        </div>
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <LogsView />
                      </div>
                    </div>
                  </motion.div>
                </div>
              )}

              {activeTab === 'map' && (
                <div className="w-full h-full flex flex-col gap-2">
                  {/* Top Section: Maps Split */}
                  <div className="flex-[7] flex gap-2 min-h-0">
                    <div className="flex-[2] glass rounded-xl overflow-hidden p-1 flex flex-col">
                      <div className="px-2 py-1 text-xs font-bold text-gray-400">Individual Stocks</div>
                      <MarketMap filterType="STOCK" />
                    </div>
                    <div className="flex-[2] glass rounded-xl overflow-hidden p-1 flex flex-col">
                      <div className="px-2 py-1 text-xs font-bold text-gray-400">Market Indices & Sector Groups</div>
                      <MarketMap filterType="MARKET" />
                    </div>
                  </div>
                  {/* Bottom Section: Sector Performance */}
                  <div className="flex-[3] glass rounded-xl overflow-hidden p-2">
                    <div className="h-full w-full">
                      <SectorPerformance />
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'logs' && (
                <div className="w-full h-full glass rounded-xl overflow-hidden p-2">
                  <LogsView />
                </div>
              )}

              {activeTab === 'system' && (
                <div className="w-full h-full flex items-center justify-center">
                  <SystemDashboard />
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
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
