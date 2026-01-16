import React from 'react';
import { MOCK_NEWS, MOCK_SECTORS } from '../mocks/marketMocks';

interface MarketInfoPanelProps {
    symbol: string;
}

export const MarketInfoPanel: React.FC<MarketInfoPanelProps> = ({ symbol }) => {
    // Mock Logic: Find sector for current symbol to show related stocks
    const currentSector = MOCK_SECTORS.find(s => s.children?.some(sym => sym.symbol === symbol));
    const relatedStocks = currentSector ? currentSector.children.filter(s => s.symbol !== symbol) : [];

    // Mock Logic: Filter news for symbol (or generic news if none)
    const news = MOCK_NEWS.filter(n => n.symbol === symbol).length > 0
        ? MOCK_NEWS.filter(n => n.symbol === symbol)
        : MOCK_NEWS; // Fallback to all news for demo

    return (
        <div className="flex-1 flex flex-col glass rounded-xl overflow-hidden shadow-lg border border-white/5 min-h-0">
            {/* Header */}
            <div className="flex items-center px-4 py-2 border-b border-white/5 bg-white/5 shrink-0">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Market Insights</span>
            </div>

            <div className="flex-1 flex flex-col min-h-0">
                {/* Section 1: Related Stocks (Flex-1) */}
                <div className="flex-1 flex flex-col min-h-0 border-b border-white/5 relative group">
                    <div className="px-3 py-1.5 bg-gray-800/30 flex items-center justify-between shrink-0">
                        <span className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Related Stocks in Sector</span>
                        {currentSector && (
                            <span className="text-[10px] text-gray-500 font-mono">{currentSector.name}</span>
                        )}
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 scrollbar-hide space-y-2">
                        {/* Sector ETF Highlight */}
                        {currentSector?.etf && (
                            <div className="p-2 rounded bg-blue-900/10 border border-blue-500/10 flex items-center justify-between">
                                <div className="flex flex-col">
                                    <span className="text-[10px] text-blue-300 font-bold uppercase tracking-wider">Sector ETF</span>
                                    <span className="text-xs text-gray-300 font-medium truncate max-w-[120px]">{currentSector.etf.name}</span>
                                </div>
                                <span className={`text-xs font-mono font-bold ${currentSector.etf.change > 0 ? 'text-red-400' : 'text-blue-400'}`}>
                                    {currentSector.etf.change > 0 ? '+' : ''}{currentSector.etf.change}%
                                </span>
                            </div>
                        )}

                        {relatedStocks.length > 0 ? (
                            <div className="grid grid-cols-1 gap-1">
                                {relatedStocks.map(stock => (
                                    <div key={stock.symbol} className="flex items-center justify-between p-2 rounded hover:bg-white/5 transition-colors group/item">
                                        <div className="flex flex-col">
                                            <span className="text-xs text-gray-200 font-medium group-hover/item:text-white transition-colors">{stock.name}</span>
                                            <span className="text-[10px] text-gray-500">{stock.symbol}</span>
                                        </div>
                                        <div className="flex flex-col items-end">
                                            <span className={`text-xs font-mono font-bold ${stock.change > 0 ? 'text-red-400' : 'text-blue-400'}`}>
                                                {stock.change > 0 ? '+' : ''}{stock.change}%
                                            </span>
                                            <span className="text-[10px] text-gray-600">
                                                {(stock.marketCap / 1000000000000).toFixed(1)}T
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-4 text-xs text-gray-600">
                                No related stocks found
                            </div>
                        )}
                    </div>
                </div>

                {/* Section 2: News Trends (Flex-1) */}
                <div className="flex-1 flex flex-col min-h-0 relative">
                    <div className="px-3 py-1.5 bg-gray-800/30 flex items-center justify-between shrink-0">
                        <span className="text-[10px] text-green-400 font-bold uppercase tracking-wider">Recent News & Sentiment</span>
                        <span className="text-[10px] text-gray-500">Live Feed</span>
                    </div>

                    <div className="flex-1 overflow-y-auto p-2 scrollbar-hide space-y-2">
                        {news.map(n => (
                            <div key={n.id} className="p-2 rounded hover:bg-white/5 transition-colors border border-transparent hover:border-white/5 group/news">
                                <div className="flex justify-between items-start mb-1 gap-2">
                                    <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded uppercase tracking-wider ${n.sentiment === 'POSITIVE' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                                        }`}>
                                        {n.sentiment}
                                    </span>
                                    <span className="text-[10px] text-gray-500 whitespace-nowrap">
                                        {new Date(n.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>
                                <h4 className="text-xs text-gray-300 font-medium leading-snug group-hover/news:text-white transition-colors mb-1 line-clamp-2">
                                    {n.title}
                                </h4>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${n.sentiment === 'POSITIVE' ? 'bg-green-500' : 'bg-red-500'}`}
                                            style={{ width: `${n.impact * 100}%` }}
                                        />
                                    </div>
                                    <span className="text-[9px] text-gray-600 font-mono">Impact {n.impact.toFixed(2)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
