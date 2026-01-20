import React, { useState } from 'react';
import { Send, AlertCircle, CheckCircle2 } from 'lucide-react';
import { postJson, VIRTUAL_API_BASE } from '../../api';

interface VirtualOrderFormProps {
    symbol: string;
    onOrderPlaced?: () => void;
}

export const VirtualOrderForm: React.FC<VirtualOrderFormProps> = ({ symbol, onOrderPlaced }) => {
    const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
    const [type, setType] = useState<'LIMIT' | 'MARKET'>('LIMIT');
    const [quantity, setQuantity] = useState<number>(1);
    const [price, setPrice] = useState<number>(0);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [status, setStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setStatus(null);

        const orderData = {
            symbol,
            side,
            type,
            quantity,
            price: type === 'LIMIT' ? price : null
        };

        const result = await postJson<any>('/orders', orderData, VIRTUAL_API_BASE);

        if (result && result.status === 'FILLED') {
            setStatus({ type: 'success', message: `Order filled: ${result.filled_quantity} @ ${result.filled_price}` });
            if (onOrderPlaced) onOrderPlaced();
        } else {
            setStatus({ type: 'error', message: 'Order rejected or failed. Check balance/position.' });
        }
        setIsSubmitting(false);
    };

    return (
        <div className="glass p-5 rounded-2xl flex flex-col gap-4">
            <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest flex items-center gap-2">
                <Send size={14} className="text-blue-500" />
                Place Virtual Order: {symbol}
            </h3>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                {/* Side Toggle */}
                <div className="flex p-1 bg-black/40 rounded-xl border border-white/5">
                    <button
                        type="button"
                        onClick={() => setSide('BUY')}
                        className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${side === 'BUY' ? 'bg-red-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        BUY
                    </button>
                    <button
                        type="button"
                        onClick={() => setSide('SELL')}
                        className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${side === 'SELL' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        SELL
                    </button>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    {/* Order Type */}
                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] text-gray-500 uppercase font-bold tracking-tighter ml-1">Order Type</label>
                        <select
                            value={type}
                            onChange={(e) => setType(e.target.value as any)}
                            className="bg-black/50 border border-white/10 rounded-xl px-3 py-2 text-sm text-gray-200 outline-none focus:border-blue-500/50 transition-colors cursor-pointer"
                        >
                            <option value="LIMIT">LIMIT</option>
                            <option value="MARKET">MARKET</option>
                        </select>
                    </div>

                    {/* Quantity */}
                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] text-gray-500 uppercase font-bold tracking-tighter ml-1">Quantity</label>
                        <input
                            type="number"
                            min={1}
                            value={quantity}
                            onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                            className="bg-black/50 border border-white/10 rounded-xl px-3 py-2 text-sm text-gray-200 outline-none focus:border-blue-500/50 transition-colors"
                        />
                    </div>
                </div>

                {/* Price (Only for LIMIT) */}
                {type === 'LIMIT' && (
                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] text-gray-500 uppercase font-bold tracking-tighter ml-1">Limit Price</label>
                        <input
                            type="number"
                            value={price}
                            onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                            className="bg-black/50 border border-white/10 rounded-xl px-3 py-2 text-sm text-gray-200 outline-none focus:border-blue-500/50 transition-colors"
                            placeholder="Set price..."
                        />
                    </div>
                )}

                {/* Submit Button */}
                <button
                    disabled={isSubmitting || quantity <= 0 || (type === 'LIMIT' && price <= 0)}
                    className={`mt-2 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${isSubmitting
                            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                            : side === 'BUY'
                                ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/20'
                                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/20'
                        }`}
                >
                    {isSubmitting ? (
                        <RefreshCcw size={16} className="animate-spin" />
                    ) : (
                        <Send size={16} />
                    )}
                    {side === 'BUY' ? 'Execute Buy' : 'Execute Sell'}
                </button>

                {/* Status Message */}
                {status && (
                    <div className={`mt-2 p-3 rounded-xl border flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300 ${status.type === 'success' ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'
                        }`}>
                        {status.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                        <span className="text-xs font-medium">{status.message}</span>
                    </div>
                )}
            </form>
        </div>
    );
};
