import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, Cell } from 'recharts';

interface SectorData {
    name: string;
    etfSymbol: string;
    returnRate: number; // % change
}

export const SectorPerformance: React.FC = () => {
    const [data, setData] = useState<SectorData[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const res = await axios.get('/indices/performance');
            setData(res.data);
        } catch (e) {
            console.error("Failed to fetch sector performance:", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    if (loading) return <div className="p-4 text-xs text-gray-500">Loading Performance...</div>;
    if (data.length === 0) return <div className="p-4 text-xs text-gray-500 text-center">No Correlation Data Yet</div>;

    return (
        <div className="w-full h-full flex flex-col p-4">
            <h3 className="text-sm font-bold text-gray-400 mb-4">Sector Relative Performance (vs Base)</h3>
            <div className="flex-1 min-h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart layout="vertical" data={data} margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                        <XAxis type="number" domain={['auto', 'auto']} hide />
                        <YAxis type="category" dataKey="name" stroke="#9CA3AF" fontSize={11} width={80} />
                        <Tooltip
                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                            contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
                        />
                        <ReferenceLine x={0} stroke="#4B5563" />
                        <Bar dataKey="returnRate" name="Return %" radius={[0, 4, 4, 0]} animationDuration={400}>
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.returnRate > 0 ? '#ef4444' : '#3b82f6'} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
