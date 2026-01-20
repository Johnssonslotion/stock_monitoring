import React from 'react';
import { VirtualAccount } from './VirtualAccount';
import { VirtualOrderForm } from './VirtualOrderForm';
import { VirtualOrderHistory } from './VirtualOrderHistory';
import { VirtualPnLChart } from './VirtualPnLChart';

interface VirtualPanelProps {
    symbol: string;
    isMock?: boolean;
}

export const VirtualPanel: React.FC<VirtualPanelProps> = ({ symbol, isMock = false }) => {
    return (
        <div className="w-full h-full flex flex-col md:flex-row gap-4 p-2 overflow-hidden">
            {/* Left Column: Account & History (6.5/10) */}
            <div className="flex-[6.5] flex flex-col min-h-0 min-w-0">
                <div className="shrink-0">
                    <VirtualAccount isMock={isMock} />
                </div>
                <div className="px-4 py-2">
                    <VirtualPnLChart isMock={isMock} />
                </div>
                <div className="flex-1 min-h-0">
                    <VirtualOrderHistory isMock={isMock} />
                </div>
            </div>

            {/* Right Column: Trading Form & Active Control (3.5/10) */}
            <div className="flex-[3.5] flex flex-col gap-4 min-w-[320px]">
                <VirtualOrderForm symbol={symbol} />

                <div className="glass p-5 rounded-2xl flex flex-col gap-3 flex-1 border border-blue-500/10 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl -z-10 rounded-full" />
                    <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest">Simulation Context</h3>
                    <div className="text-xs text-gray-400 leading-relaxed">
                        This environment simulates a standard KR/US broker with the following parameters:
                        <ul className="mt-2 list-disc list-inside flex flex-col gap-1 opacity-80">
                            <li>Commission: <span className="text-blue-400 font-mono">0.015%</span></li>
                            <li>KR Tax: <span className="text-blue-400 font-mono">0.18%</span> (Cell)</li>
                            <li>Execution: <span className="text-green-400">Immediate</span> (Best Ask/Bid)</li>
                        </ul>
                    </div>
                    <div className="mt-auto p-3 bg-blue-500/10 rounded-xl border border-blue-500/20">
                        <div className="text-[10px] text-blue-400 font-bold uppercase tracking-widest mb-1">Status</div>
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-lg shadow-green-500/50" />
                            <span className="text-xs text-gray-200">System Live & Connected</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
