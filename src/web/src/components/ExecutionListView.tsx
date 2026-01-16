import React, { useEffect, useState } from 'react';
import { EXECUTIONS_BY_SYMBOL, type Execution } from '../mocks/tradingMocks';

interface ExecutionListViewProps {
    symbol: string;
}

export const ExecutionListView: React.FC<ExecutionListViewProps> = ({ symbol }) => {
    const [executions, setExecutions] = useState<Execution[]>([]);

    useEffect(() => {
        // 심볼 변경 시 데이터 클리어 후
        setExecutions([]); // Clear on symbol change

        const timer = setTimeout(() => {
            const mockData = EXECUTIONS_BY_SYMBOL[symbol] || [];
            setExecutions(mockData);
        }, 100);

        return () => clearTimeout(timer);
    }, [symbol]);

    // 평균 거래량 계산 (대량 체결 판단용)
    const avgVolume = executions.length > 0
        ? executions.reduce((sum, e) => sum + e.volume, 0) / executions.length
        : 0;

    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-3 py-2 bg-gray-800/50 border-b border-white/5 shrink-0">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Time & Sales (체결)</span>
            </div>

            {/* Executions List */}
            <div className="flex-1 overflow-y-auto">
                <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-gray-900 text-[10px] text-gray-500 uppercase">
                        <tr>
                            <th className="px-2 py-1 text-left">Time</th>
                            <th className="px-2 py-1 text-right">Price</th>
                            <th className="px-2 py-1 text-right">Volume</th>
                            <th className="px-2 py-1 text-center">Type</th>
                        </tr>
                    </thead>
                    <tbody>
                        {executions.map((exec, idx) => {
                            const isLargeVolume = exec.volume > avgVolume * 5; // 5배 이상 = 대량 체결
                            const rowBg = isLargeVolume ? 'bg-yellow-500/10' : '';
                            const typeColor = exec.type === 'BUY' ? 'text-red-400' : 'text-blue-400';
                            const changeColor = exec.change > 0 ? 'text-red-400' : exec.change < 0 ? 'text-blue-400' : 'text-gray-400';

                            return (
                                <tr key={idx} className={`border-b border-gray-800/50 hover:bg-gray-800/30 ${rowBg}`}>
                                    <td className="px-2 py-1.5 font-mono text-gray-400 text-[10px]">
                                        {exec.time}
                                    </td>
                                    <td className={`px-2 py-1.5 text-right font-mono font-bold ${changeColor}`}>
                                        {exec.price.toLocaleString()}
                                    </td>
                                    <td className="px-2 py-1.5 text-right font-mono text-gray-300">
                                        {exec.volume.toLocaleString()}
                                        {isLargeVolume && <span className="ml-1 text-[10px]">🔥</span>}
                                    </td>
                                    <td className="px-2 py-1.5 text-center">
                                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${typeColor} bg-current bg-opacity-10`}>
                                            {exec.type}
                                        </span>
                                    </td>
                                </tr>
                            );
                        })}
                        {executions.length === 0 && (
                            <tr>
                                <td colSpan={4} className="text-center py-8 text-gray-500 text-xs">
                                    <div className="animate-pulse">Waiting for executions...</div>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
