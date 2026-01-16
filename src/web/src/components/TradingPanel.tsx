import React from 'react';
import { OrderBookView } from './OrderBookView';
import { VolumeHistogram } from './VolumeHistogram';
import { MarketInfoPanel } from './MarketInfoPanel';

interface TradingPanelProps {
    symbol: string;
}

export const TradingPanel: React.FC<TradingPanelProps> = ({ symbol }) => {
    return (
        <div className="w-full h-full flex flex-col gap-1">
            {/* Top Row: Volume Flow + OrderBook (Reduced Height, Min Height Guaranteed) */}
            <div className="flex-[4] flex gap-1 min-h-[300px] shrink-0">
                {/* Volume Histogram */}
                <div className="flex-[4] glass rounded-lg overflow-hidden min-h-0">
                    <VolumeHistogram />
                </div>

                {/* Order Book */}
                <div className="flex-[6] glass rounded-lg overflow-hidden min-h-0 flex flex-col">
                    <OrderBookView symbol={symbol} simple={true} />
                </div>
            </div>

            {/* Bottom Row: Market Info (Related Stocks & News) - Increased Height */}
            <div className="flex-[6] glass rounded-lg overflow-hidden min-h-0">
                <MarketInfoPanel symbol={symbol} />
            </div>
        </div>
    );
};
