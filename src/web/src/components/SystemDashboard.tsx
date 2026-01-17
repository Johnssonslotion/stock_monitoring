import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity, Box, ShieldCheck } from 'lucide-react';
import { streamManager } from '../StreamManager';

interface Metric {
    time: string;
    type: string;
    value: number;
    meta?: any;
}

export const SystemDashboard: React.FC = () => {
    const [chartData, setChartData] = useState<any[]>([]);
    const [containerStatus, setContainerStatus] = useState<Record<string, string>>({});
    const [governance, setGovernance] = useState<any>({
        status: 'Checking...',
        compliance_score: 0,
        last_audit: '-'
    });

    const fetchInitialData = async () => {
        try {
            const [metricsRes, govRes] = await Promise.all([
                axios.get('/api/system/metrics', { params: { limit: 100 } }),
                axios.get('/api/system/governance/status')
            ]);

            // Process Initial Chart Data
            const grouped: Record<string, any> = {};
            const containers: Record<string, string> = {};

            [...metricsRes.data].reverse().forEach((m: Metric) => {
                if (m.type === 'container_status' && m.meta?.container) {
                    containers[m.meta.container] = m.meta.status;
                }
                if (['cpu', 'memory', 'disk'].includes(m.type)) {
                    const timeKey = new Date(m.time).toLocaleTimeString();
                    if (!grouped[timeKey]) grouped[timeKey] = { time: timeKey };
                    grouped[timeKey][m.type] = m.value;
                }
            });

            setChartData(Object.values(grouped));
            setContainerStatus(containers);
            setGovernance(govRes.data);
        } catch (e) {
            console.error("Failed to fetch initial monitoring data", e);
        }
    };

    useEffect(() => {
        fetchInitialData();

        // 1. Listen for Real-time Metrics
        const handleMetric = (m: any) => {
            if (['cpu', 'memory', 'disk'].includes(m.type)) {
                const timeKey = new Date(m.timestamp || m.time).toLocaleTimeString();
                setChartData(prev => {
                    const newData = [...prev];
                    const last = newData[newData.length - 1];

                    if (last && last.time === timeKey) {
                        last[m.type] = m.value;
                        return newData;
                    } else {
                        const newEntry = { time: timeKey, [m.type]: m.value };
                        return [...newData.slice(-99), newEntry];
                    }
                });
            } else if (m.type === 'governance_status') {
                setGovernance(m.meta);
            }
        };

        // 2. Listen for Container Updates
        const handleContainer = (m: any) => {
            if (m.meta?.container) {
                setContainerStatus(prev => ({
                    ...prev,
                    [m.meta.container]: m.meta.status
                }));
            }
        };

        streamManager.on('system_metric', handleMetric);
        streamManager.on('container_status', handleContainer);

        return () => {
            streamManager.off('system_metric', handleMetric);
            streamManager.off('container_status', handleContainer);
        };
    }, []);

    return (
        <div className="w-full h-full flex flex-col gap-4 p-4 overflow-y-auto">
            {/* 0. Governance Health Card */}
            <div className="glass p-4 rounded-xl flex items-center justify-between border-l-4 border-green-500 bg-green-500/5">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-green-500/20 rounded-full text-green-400">
                        <ShieldCheck size={24} />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-white">Governance Compliance</h2>
                        <p className="text-sm text-gray-400">Version {governance.constitution_version} | Finalized on {governance.last_audit}</p>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-3xl font-black text-green-400">{governance.compliance_score}%</div>
                    <div className="text-[10px] uppercase tracking-widest text-gray-500">System Integrity</div>
                </div>
            </div>

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
