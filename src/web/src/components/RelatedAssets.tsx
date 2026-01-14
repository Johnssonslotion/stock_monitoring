import React, { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { TrendingUp, TrendingDown, Layers } from 'lucide-react';

interface RelatedAsset {
    symbol: string;
    name: string;
    type: 'ETF' | 'SECTOR';
    change: number;
    price: number;
}

interface RelatedAssetsProps {
    symbol: string; // 현재 선택된 종목 코드
    name: string;   // 현재 선택된 종목명
}

// Mock Mapping Data (나중에는 API로 대체)
const MOCK_RELATIONS: Record<string, RelatedAsset[]> = {
    '005930': [ // 삼성전자
        { symbol: '069500', name: 'KODEX 200', type: 'ETF', change: 1.2, price: 34500 },
        { symbol: '091160', name: 'KODEX 반도체', type: 'ETF', change: 2.5, price: 28900 },
        { symbol: 'KRX_IT', name: 'KRX 정보기술', type: 'SECTOR', change: 1.8, price: 1250 }
    ],
    '000660': [ // SK하이닉스
        { symbol: '091160', name: 'KODEX 반도체', type: 'ETF', change: 2.5, price: 28900 },
        { symbol: '305540', name: 'TIGER 2차전지테마', type: 'ETF', change: -0.5, price: 15400 } // 예시
    ],
    '373220': [ // LG에너지솔루션
        { symbol: '305540', name: 'TIGER 2차전지테마', type: 'ETF', change: -1.2, price: 15200 },
        { symbol: '051910', name: 'LG화학', type: 'SECTOR', change: -0.8, price: 485000 } // 그룹사
    ]
};

export const RelatedAssets: React.FC<RelatedAssetsProps> = ({ symbol, name }) => {
    const [assets, setAssets] = useState<RelatedAsset[]>([]);

    useEffect(() => {
        // Mock Fetching
        const relations = MOCK_RELATIONS[symbol] || [
            { symbol: '069500', name: 'KODEX 200', type: 'ETF', change: 0.5, price: 34000 } // Default Fallback
        ];
        setAssets(relations);
    }, [symbol]);

    return (
        <div className="flex flex-col h-full glass rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-white/5 bg-white/5 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Layers size={14} className="text-blue-400" />
                    <span className="text-xs font-bold text-gray-200 uppercase tracking-wider">Related Context</span>
                </div>
                <span className="text-[10px] text-gray-400 bg-black/20 px-2 py-0.5 rounded-full">
                    {name}
                </span>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-4">
                {/* Section 1: Related Assets */}
                <div className="space-y-2">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1">
                        Correlated Assets
                    </div>
                    {assets.map((asset) => (
                        <div key={asset.symbol} className="flex items-center justify-between p-2 rounded-lg bg-black/20 hover:bg-white/5 transition-colors border border-white/5 group checkbox-selection cursor-pointer">
                            <div className="flex flex-col">
                                <div className="flex items-center gap-2">
                                    <span className={clsx(
                                        "text-[9px] font-bold px-1.5 py-0.5 rounded",
                                        asset.type === 'ETF' ? "bg-purple-500/20 text-purple-300" : "bg-blue-500/20 text-blue-300"
                                    )}>
                                        {asset.type}
                                    </span>
                                    <span className="text-xs font-bold text-gray-200">{asset.name}</span>
                                </div>
                                <span className="text-[10px] text-gray-500 ml-1">{asset.symbol}</span>
                            </div>

                            <div className="text-right">
                                <div className="text-xs font-mono font-medium text-gray-200">
                                    {asset.price.toLocaleString()}
                                </div>
                                <div className={clsx(
                                    "flex items-center justify-end gap-1 text-[10px] font-bold",
                                    asset.change > 0 ? "text-red-400" : asset.change < 0 ? "text-blue-400" : "text-gray-400"
                                )}>
                                    {asset.change > 0 && <TrendingUp size={10} />}
                                    {asset.change < 0 && <TrendingDown size={10} />}
                                    {asset.change > 0 ? '+' : ''}{asset.change}%
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Section 2: Recent News (New) */}
                <div className="space-y-2">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1 pt-2 border-t border-white/5">
                        Recent News / Sentiment
                    </div>
                    <div className="flex flex-col gap-2">
                        {/* Mock News 1 */}
                        <div className="p-2 rounded-lg bg-white/5 hover:bg-white/10 cursor-pointer transition-colors border-l-2 border-blue-500">
                            <div className="text-xs text-gray-200 leading-snug mb-1">
                                [특징주] {name}, 외국인 5일 연속 순매수... 반도체 업황 회복 기대감
                            </div>
                            <div className="flex justify-between items-center text-[10px] text-gray-500">
                                <span>이데일리</span>
                                <span>10:30 AM</span>
                            </div>
                        </div>
                        {/* Mock News 2 */}
                        <div className="p-2 rounded-lg bg-white/5 hover:bg-white/10 cursor-pointer transition-colors border-l-2 border-gray-600">
                            <div className="text-xs text-gray-200 leading-snug mb-1">
                                {name} 4분기 영업익 2.8조 전망... 컨센서스 상회할까
                            </div>
                            <div className="flex justify-between items-center text-[10px] text-gray-500">
                                <span>한국경제</span>
                                <span>09:15 AM</span>
                            </div>
                        </div>
                    </div>
                </div>

                {assets.length === 0 && (
                    <div className="text-center py-8 text-gray-500 text-xs">
                        No related information found.
                    </div>
                )}
            </div>

            <div className="p-2 border-t border-white/5 bg-black/20 text-[10px] text-gray-500 text-center">
                AI-driven Correlation Analysis
            </div>
        </div>
    );
};
