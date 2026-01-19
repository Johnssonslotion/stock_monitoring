import React, { useState, useEffect } from 'react';
import { Wallet, TrendingUp, TrendingDown, RefreshCcw } from 'lucide-react';
import { fetchJson, VIRTUAL_API_BASE } from '../../api';
import { MOCK_VIRTUAL_ACCOUNT, MOCK_VIRTUAL_POSITIONS } from '../../mocks/virtualMocks';

interface VirtualAccountProps {
    isMock?: boolean;
}

export const VirtualAccount: React.FC<VirtualAccountProps> = ({ isMock = false }) => {
    const [account, setAccount] = useState<any>(null);
    const [positions, setPositions] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchData = async () => {
        setIsLoading(true);
        if (isMock) {
            setAccount(MOCK_VIRTUAL_ACCOUNT);
            setPositions(MOCK_VIRTUAL_POSITIONS);
        } else {
            const accData = await fetchJson<any>('/account', VIRTUAL_API_BASE);
            const posData = await fetchJson<any>('/positions', VIRTUAL_API_BASE);
            if (accData) setAccount(accData);
            if (posData) setPositions(posData.positions || []);
        }
        setIsLoading(false);
    };

    useEffect(() => {
        fetchData();
    }, [isMock]);

    if (isLoading) return <div className="p-4 animate-pulse text-gray-400">Loading Account...</div>;
    if (!account) return <div className="p-4 text-red-400">Failed to load virtual account.</div>;

    const totalPositionValue = positions.reduce((acc, pos) => acc + (pos.current_price * pos.quantity), 0);
    const totalAssetValue = account.balance + totalPositionValue;
    const totalPnL = positions.reduce((acc, pos) => acc + pos.unrealized_pnl, 0);

    return (
        <div className="flex flex-col gap-4 p-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass p-5 rounded-2xl flex flex-col gap-2 border-l-4 border-l-blue-500">
                    <div className="flex items-center justify-between text-gray-400">
                        <span className="text-xs font-bold uppercase tracking-wider">Available Balance</span>
                        <Wallet size={16} />
                    </div>
                    <div className="text-2xl font-bold text-white">
                        {account.balance.toLocaleString()} <span className="text-sm font-normal text-gray-400">{account.currency}</span>
                    </div>
                </div>

                <div className="glass p-5 rounded-2xl flex flex-col gap-2 border-l-4 border-l-purple-500">
                    <div className="flex items-center justify-between text-gray-400">
                        <span className="text-xs font-bold uppercase tracking-wider">Total Assets</span>
                        <TrendingUp size={16} />
                    </div>
                    <div className="text-2xl font-bold text-white">
                        {totalAssetValue.toLocaleString()} <span className="text-sm font-normal text-gray-400">{account.currency}</span>
                    </div>
                </div>

                <div className={`glass p-5 rounded-2xl flex flex-col gap-2 border-l-4 ${totalPnL >= 0 ? 'border-l-green-500' : 'border-l-red-500'}`}>
                    <div className="flex items-center justify-between text-gray-400">
                        <span className="text-xs font-bold uppercase tracking-wider">Unrealized PnL</span>
                        {totalPnL >= 0 ? <TrendingUp size={16} className="text-green-500" /> : <TrendingDown size={16} className="text-red-500" />}
                    </div>
                    <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {totalPnL >= 0 ? '+' : ''}{totalPnL.toLocaleString()}
                        <span className="text-sm font-normal opacity-70 ml-2">
                            ({((totalPnL / (totalAssetValue - totalPnL)) * 100).toFixed(2)}%)
                        </span>
                    </div>
                </div>
            </div>

            {/* Positions Table */}
            <div className="glass rounded-2xl overflow-hidden mt-2">
                <div className="px-5 py-3 border-b border-white/5 bg-white/5 flex justify-between items-center">
                    <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest">Current Positions</h3>
                    <button onClick={fetchData} className="text-gray-400 hover:text-white transition-colors">
                        <RefreshCcw size={14} className={isLoading ? 'animate-spin' : ''} />
                    </button>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-white/5 text-gray-400 text-[10px] uppercase font-bold tracking-tighter">
                            <tr>
                                <th className="px-5 py-3">Symbol</th>
                                <th className="px-5 py-3">Quantity</th>
                                <th className="px-5 py-3">Avg Price</th>
                                <th className="px-5 py-3">Current</th>
                                <th className="px-5 py-3 text-right">PnL</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {positions.length > 0 ? positions.map((pos) => (
                                <tr key={pos.symbol} className="hover:bg-white/5 transition-colors group">
                                    <td className="px-5 py-4 font-bold text-blue-400 group-hover:text-blue-300">{pos.symbol}</td>
                                    <td className="px-5 py-4 text-gray-300">{pos.quantity.toLocaleString()}</td>
                                    <td className="px-5 py-4 text-gray-400">{pos.avg_price.toLocaleString()}</td>
                                    <td className="px-5 py-4 text-gray-200 font-medium">{pos.current_price.toLocaleString()}</td>
                                    <td className={`px-5 py-4 text-right font-bold ${pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl.toLocaleString()}
                                        <div className="text-[10px] font-normal opacity-60">{pos.unrealized_pnl_pct.toFixed(2)}%</div>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan={5} className="px-5 py-8 text-center text-gray-500 italic">No active positions found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};
