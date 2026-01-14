import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity, Box } from 'lucide-react';

interface Metric {
    time: string;
    type: string;
    value: number;
    meta?: any;
}

export const SystemDashboard: React.FC = () => {
    const [chartData, setChartData] = useState<any[]>([]);
    const [containerStatus, setContainerStatus] = useState<Record<string, string>>({});

    const fetchMetrics = async () => {
        try {
            const res = await axios.get('/system/metrics', { params: { limit: 100 } });
            const data = res.data;

            // Process Chart Data (Pivot by time)
            const groupedArgs: Record<string, any> = {};
            const containers: Record<string, string> = {};

            // Sort by time ascending for chart
            const sortedData = [...data].reverse();

            sortedData.forEach((m: Metric) => {
                // For Container Status (Latest only)
                if (m.type === 'container_status' && m.meta?.container) {
                    containers[m.meta.container] = m.meta.status;
                }

                // For Chart (Host Metrics)
                if (['cpu', 'memory', 'disk'].includes(m.type)) {
                    const timeKey = new Date(m.time).toLocaleTimeString();
                    if (!groupedArgs[timeKey]) groupedArgs[timeKey] = { time: timeKey };
                    groupedArgs[timeKey][m.type] = m.value;
                }
            });

            setChartData(Object.values(groupedArgs));
            setContainerStatus(containers);
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        fetchMetrics();
        const interval = setInterval(fetchMetrics, 5000); // 5s Poll
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="w-full h-full flex flex-col gap-4 p-4 overflow-y-auto">
            {/* 1. Container Health Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {Object.entries(containerStatus).map(([name, status]) => (
                    <div key={name} className="glass p-3 rounded-lg flex flex-col items-center justify-center relative overflow-hidden group">
                        <div className={`absolute inset-0 opacity-10 ${status === 'running' ? 'bg-green-500' : 'bg-red-500'}`} />
                        <Box className={`w-6 h-6 mb-2 ${status === 'running' ? 'text-green-400' : 'text-red-400'}`} />
                        <span className="text-xs font-bold text-gray-300 truncate w-full text-center" title={name}>
                            {name}
                        </span>
                        <span className={`text-[10px] uppercase font-mono mt-1 ${status === 'running' ? 'text-green-500' : 'text-red-500'}`}>
                            {status}
                        </span>
                    </div>
                ))}
            </div>

            {/* 2. System Resource Charts */}
            <div className="flex-1 min-h-[300px] glass rounded-xl p-4 flex flex-col">
                <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                    <Activity size={16} /> Host Resources (CPU / Memory / Disk)
                </h3>
                <div className="flex-1 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                            <XAxis dataKey="time" stroke="#666" fontSize={10} tick={{ fill: '#666' }} />
                            <YAxis stroke="#666" fontSize={10} domain={[0, 100]} tick={{ fill: '#666' }} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }}
                                itemStyle={{ fontSize: '12px' }}
                            />
                            <Legend />
                            <Line type="monotone" dataKey="cpu" stroke="#ef4444" strokeWidth={2} dot={false} name="CPU %" />
                            <Line type="monotone" dataKey="memory" stroke="#3b82f6" strokeWidth={2} dot={false} name="Mem %" />
                            <Line type="monotone" dataKey="disk" stroke="#10b981" strokeWidth={2} dot={false} name="Disk %" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};
