import { useState, useEffect } from 'react'

interface Infrastructure {
  cpu?: number;
  memory?: number;
  disk?: number;
}

interface Service {
  name: string;
  status: string;
  is_running: boolean;
  last_updated: string;
}

interface StatusData {
  timestamp: string;
  infrastructure: Infrastructure;
  services: Service[];
}

function App() {
  const [data, setData] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_STATUS_API_URL || 'http://localhost:8080';
  const API_KEY = import.meta.env.VITE_API_KEY || 'super-secret-key';

  const fetchData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/status`, {
        headers: {
          'X-API-KEY': API_KEY
        }
      });
      if (!response.ok) throw new Error('Failed to fetch status');
      const json = await response.json();
      setData(json);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // 10s refresh
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="text-primary animate-pulse">Initializing Sentinel Bridge...</div>;

  return (
    <div className="min-h-screen bg-background p-8 text-white">
      <header className="mb-12 flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold text-primary tracking-tight">Sentinel Bridge</h1>
          <p className="text-slate-400 mt-2">External Infrastructure Monitor</p>
        </div>
        <div className="text-right">
          <div className="text-sm text-slate-500">Last Synced</div>
          <div className="font-mono text-success text-lg">
            {data ? new Date(data.timestamp).toLocaleTimeString() : 'N/A'}
          </div>
        </div>
      </header>

      {error && (
        <div className="bg-danger/20 border border-danger p-4 rounded-xl mb-8 text-danger flex items-center gap-3">
          <span className="text-2xl">⚠️</span> {error}
        </div>
      )}

      {/* Infrastructure Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <MetricCard label="CPU Usage" value={data?.infrastructure.cpu} unit="%" color="primary" />
        <MetricCard label="Memory" value={data?.infrastructure.memory} unit="%" color="primary" />
        <MetricCard label="Disk Space" value={data?.infrastructure.disk} unit="%" color="primary" />
      </section>

      {/* Services Grid */}
      <h2 className="text-2xl font-semibold mb-6 text-slate-300">Container Fleet Status</h2>
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {data?.services.map((svc) => (
          <div key={svc.name} className="bg-card p-5 rounded-2xl border border-slate-800 hover:border-slate-600 transition-all group">
            <div className="flex justify-between items-start mb-4">
              <div className="text-lg font-medium group-hover:text-primary transition-colors">{svc.name}</div>
              <StatusBadge running={svc.is_running} />
            </div>
            <div className="text-xs text-slate-500 font-mono">
              STATUS: <span className={svc.is_running ? 'text-success' : 'text-danger'}>{svc.status.toUpperCase()}</span>
            </div>
            <div className="text-[10px] text-slate-600 mt-3 pt-3 border-t border-slate-800">
              UPDATED: {new Date(svc.last_updated).toLocaleString()}
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}

function MetricCard({ label, value, unit, color }: any) {
  const percent = value || 0;
  return (
    <div className="bg-card p-6 rounded-3xl border border-slate-800 flex flex-col items-center">
      <div className="text-slate-400 mb-2 font-medium">{label}</div>
      <div className="relative w-32 h-32 flex items-center justify-center">
        {/* Simple Progress Ring simulation */}
        <svg className="absolute w-full h-full -rotate-90">
          <circle cx="64" cy="64" r="58" fill="none" stroke="#0f172a" strokeWidth="8" />
          <circle cx="64" cy="64" r="58" fill="none" stroke="currentColor" strokeWidth="8"
            strokeDasharray="364" strokeDashoffset={364 - (364 * percent / 100)}
            className={`text-${color} transition-all duration-1000`} />
        </svg>
        <div className="text-3xl font-bold font-mono">
          {percent}
          <span className="text-sm ml-1 opacity-50">{unit}</span>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ running }: { running: boolean }) {
  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider ${running ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
      }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${running ? 'bg-success' : 'bg-danger animate-pulse'}`}></span>
      {running ? 'OPERATIONAL' : 'DOWN'}
    </div>
  )
}

export default App
