import { useEffect, useState } from 'react';
import { Activity, Server, WifiOff } from 'lucide-react';

interface SystemInfo {
    env: string;
    hostname: string;
    version: string;
}

export const ServerStatus = () => {
    const [info, setInfo] = useState<SystemInfo | null>(null);
    const [error, setError] = useState(false);

    useEffect(() => {
        const fetchInfo = async () => {
            try {
                // Determine API URL (Vite Proxy or Direct)
                const apiUrl = import.meta.env.VITE_API_URL || '';
                const res = await fetch(`${apiUrl}/system/info`);
                if (!res.ok) throw new Error('Failed to fetch');
                const data = await res.json();
                setInfo(data);
                setError(false);
            } catch (e) {
                console.error(e);
                setError(true);
            }
        };

        fetchInfo();
        const interval = setInterval(fetchInfo, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    if (error) {
        return (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-medium backdrop-blur-md">
                <WifiOff size={14} />
                <span>Disconnected</span>
            </div>
        );
    }

    if (!info) {
        return (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-500/10 border border-gray-500/20 text-gray-400 text-xs font-medium backdrop-blur-md animate-pulse">
                <Activity size={14} />
                <span>Connecting...</span>
            </div>
        );
    }

    const isProd = info.env === 'production' || info.hostname.includes('oracle'); // Heuristic detection

    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium backdrop-blur-md transition-colors
            ${isProd
                ? 'bg-green-500/10 border-green-500/20 text-green-500'
                : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500'
            }`}
        >
            <Server size={14} />
            <span className="uppercase tracking-wider">
                {isProd ? `SERVER (${info.hostname})` : `LOCAL (${info.env})`}
            </span>
        </div>
    );
};
