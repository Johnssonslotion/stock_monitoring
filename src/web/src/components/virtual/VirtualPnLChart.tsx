import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { fetchJson, VIRTUAL_API_BASE } from '../../api';

interface VirtualPnLChartProps {
    isMock?: boolean;
}

export const VirtualPnLChart: React.FC<VirtualPnLChartProps> = ({ isMock = false }) => {
    const [data, setData] = useState<any[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            if (isMock) {
                // Generate some mock PnL history
                const mockHistory = [];
                let pnl = 0;
                const now = new Date();
                for (let i = 24; i >= 0; i--) {
                    pnl += (Math.random() - 0.45) * 500000;
                    const date = new Date(now.getTime() - i * 3600 * 1000);
                    mockHistory.push({
                        time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                        pnl: Math.round(pnl)
                    });
                }
                setData(mockHistory);
            } else {
                // In a real app, you'd fetch PnL history from an endpoint
                // For now, we'll use a simplified mock even in "real" mode if endpoint doesn't exist
                const pnlData = await fetchJson<any>('/pnl', VIRTUAL_API_BASE);
                if (pnlData) {
                    // Transform or set data
                }
            }
        };
        fetchData();
    }, [isMock]);

    return (
        <div className="glass p-5 rounded-2xl flex flex-col gap-4 h-[300px]">
            <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest">PnL Performance (24h)</h3>
            <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                        <XAxis
                            dataKey="time"
                            stroke="#666"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                            interval={4}
                        />
                        <YAxis
                            stroke="#666"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(value) => `${(value / 10000).toFixed(0)}만`}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '8px', fontSize: '12px' }}
                            itemStyle={{ color: '#3b82f6' }}
                        />
                        <Area
                            type="monotone"
                            dataKey="pnl"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorPnl)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
