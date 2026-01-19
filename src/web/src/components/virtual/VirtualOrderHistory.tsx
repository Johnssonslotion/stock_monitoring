import React, { useState, useEffect } from 'react';
import { History, Search, Filter } from 'lucide-react';
import { fetchJson, VIRTUAL_API_BASE } from '../../api';
import { MOCK_VIRTUAL_ORDERS } from '../../mocks/virtualMocks';

interface VirtualOrderHistoryProps {
    isMock?: boolean;
}

export const VirtualOrderHistory: React.FC<VirtualOrderHistoryProps> = ({ isMock = false }) => {
    const [orders, setOrders] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchOrders = async () => {
            setIsLoading(true);
            if (isMock) {
                setOrders(MOCK_VIRTUAL_ORDERS);
            } else {
                const data = await fetchJson<any>('/orders?limit=50', VIRTUAL_API_BASE);
                if (data) setOrders(data.orders || []);
            }
            setIsLoading(false);
        };
        fetchOrders();
    }, [isMock]);

    return (
        <div className="glass rounded-2xl overflow-hidden flex flex-col h-full mt-4">
            <div className="px-5 py-4 border-b border-white/5 bg-white/5 flex justify-between items-center shrink-0">
                <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest flex items-center gap-2">
                    <History size={16} className="text-gray-400" />
                    Trading History
                </h3>
                <div className="flex gap-2">
                    <div className="bg-black/40 p-1.5 rounded-lg border border-white/5 cursor-pointer hover:bg-white/5 text-gray-400">
                        <Search size={14} />
                    </div>
                    <div className="bg-black/40 p-1.5 rounded-lg border border-white/5 cursor-pointer hover:bg-white/5 text-gray-400">
                        <Filter size={14} />
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto">
                <table className="w-full text-left text-xs">
                    <thead className="bg-white/5 text-gray-400 uppercase font-bold tracking-tighter sticky top-0">
                        <tr>
                            <th className="px-5 py-3">Time</th>
                            <th className="px-5 py-3">Symbol</th>
                            <th className="px-5 py-3">Side</th>
                            <th className="px-5 py-3">Price</th>
                            <th className="px-5 py-3">Qty</th>
                            <th className="px-5 py-3 text-right">Fee/Tax</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {orders.length > 0 ? orders.map((order) => (
                            <tr key={order.order_id} className="hover:bg-white/5 transition-colors group">
                                <td className="px-5 py-4 text-gray-500 font-mono">
                                    {new Date(order.executed_at || order.created_at).toLocaleTimeString([], { hour12: false })}
                                </td>
                                <td className="px-5 py-4 font-bold text-gray-200">{order.symbol}</td>
                                <td className={`px-5 py-4 font-bold ${order.side === 'BUY' ? 'text-red-400' : 'text-blue-400'}`}>
                                    {order.side}
                                </td>
                                <td className="px-5 py-4 text-gray-300 font-medium">
                                    {order.filled_price?.toLocaleString() || order.price?.toLocaleString() || '-'}
                                </td>
                                <td className="px-5 py-4 text-gray-400">{order.quantity.toLocaleString()}</td>
                                <td className="px-5 py-4 text-right text-gray-500 font-mono">
                                    {(order.fee + order.tax).toLocaleString()}
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan={6} className="px-5 py-12 text-center text-gray-600 italic">No trading history recorded.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
