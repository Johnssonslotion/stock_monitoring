import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Activity, Database, Server, Clock } from 'lucide-react';

interface HealthStatus {
    status: string;
    db: boolean;
    redis: boolean;
    timestamp: string;
}

export const StatusPanel: React.FC = () => {
    const [health, setHealth] = useState<HealthStatus | null>(null);

    const fetchHealth = async () => {
        try {
            const res = await axios.get('/health');
            setHealth(res.data);
        } catch (e) {
            console.error(e);
            setHealth(null);
        }
    };

    useEffect(() => {
        fetchHealth();
        const interval = setInterval(fetchHealth, 10000);
        return () => clearInterval(interval);
    }, []);

    if (!health) return <div className="text-red-500">System Unreachable</div>;

    return (
        <div className="p-6 bg-gray-900 rounded-lg border border-gray-800 m-4 max-w-2xl text-gray-300">
            <h2 className="text-xl font-bold mb-4 flex items-center text-white">
                <Activity className="w-5 h-5 mr-2 text-green-500" />
                System Status
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-3 bg-gray-800 rounded">
                    <div className="flex items-center">
                        <Database className="w-4 h-4 mr-2" />
                        <span>TimescaleDB</span>
                    </div>
                    <span className={health.db ? "text-green-400" : "text-red-400"}>
                        {health.db ? "Connected" : "Disconnected"}
                    </span>
                </div>

                <div className="flex items-center justify-between p-3 bg-gray-800 rounded">
                    <div className="flex items-center">
                        <Server className="w-4 h-4 mr-2" />
                        <span>Redis (Pub/Sub)</span>
                    </div>
                    <span className={health.redis ? "text-green-400" : "text-red-400"}>
                        {health.redis ? "Connected" : "Disconnected"}
                    </span>
                </div>

                <div className="flex items-center justify-between p-3 bg-gray-800 rounded col-span-full">
                    <div className="flex items-center">
                        <Clock className="w-4 h-4 mr-2" />
                        <span>Last Check</span>
                    </div>
                    <span>{new Date(health.timestamp).toLocaleString()}</span>
                </div>
            </div>
        </div>
    );
};
