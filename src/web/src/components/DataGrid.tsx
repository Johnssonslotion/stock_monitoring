import React from 'react';
import { format } from 'date-fns';

interface LogRecord {
    time: string;
    symbol: string;
    price: number;
    volume: number;
    change?: number;
}

interface DataGridProps {
    data: LogRecord[];
}

export const DataGrid: React.FC<DataGridProps> = ({ data }) => {
    return (
        <div className="w-full h-full overflow-hidden flex flex-col bg-gray-900 border border-gray-800 rounded-lg">
            <div className="p-3 bg-gray-800 border-b border-gray-700 font-semibold text-sm text-gray-200">
                Live Data Inspector (Latest 50 Ticks)
            </div>
            <div className="flex-1 overflow-auto">
                <table className="w-full text-xs text-left text-gray-400">
                    <thead className="text-xs text-gray-500 uppercase bg-gray-900 sticky top-0">
                        <tr>
                            <th className="px-4 py-2">Time</th>
                            <th className="px-4 py-2">Symbol</th>
                            <th className="px-4 py-2 text-right">Price</th>
                            <th className="px-4 py-2 text-right">Volume</th>
                            <th className="px-4 py-2 text-right">Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, idx) => (
                            <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                                <td className="px-4 py-2 whitespace-nowrap">
                                    {format(new Date(row.time), 'HH:mm:ss.SSS')}
                                </td>
                                <td className="px-4 py-2 font-medium text-blue-400">{row.symbol}</td>
                                <td className="px-4 py-2 text-right text-gray-200">
                                    {row.price.toLocaleString()}
                                </td>
                                <td className="px-4 py-2 text-right text-gray-400">
                                    {row.volume.toLocaleString()}
                                </td>
                                <td className={`px-4 py-2 text-right ${(row.change || 0) > 0 ? 'text-red-400' :
                                        (row.change || 0) < 0 ? 'text-blue-400' : 'text-gray-400'
                                    }`}>
                                    {row.change}%
                                </td>
                            </tr>
                        ))}
                        {data.length === 0 && (
                            <tr>
                                <td colSpan={5} className="text-center py-8 text-gray-500">
                                    No data received yet...
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
