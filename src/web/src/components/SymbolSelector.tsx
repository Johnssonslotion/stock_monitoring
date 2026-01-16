import React, { useState } from 'react';
import { clsx } from 'clsx';
import { Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface SymbolSelectorProps {
    currentSymbol: string;
    onChange: (symbol: string, name: string) => void;
}

// Mock Search Results for now (Later DB connected)
const AVAILABLE_SYMBOLS = [
    { code: "005930", name: "Samsung Elec", type: "KOSPI" },
    { code: "000660", name: "SK Hynix", type: "KOSPI" },
    { code: "005380", name: "Hyundai Motor", type: "KOSPI" },
    { code: "035420", name: "NAVER", type: "KOSPI" },
    { code: "035720", name: "Kakao", type: "KOSPI" },
    { code: "068270", name: "Celltrion", type: "KOSPI" },
    { code: "373220", name: "LG Energy Sol", type: "KOSPI" }
];

export const SymbolSelector: React.FC<SymbolSelectorProps> = ({ currentSymbol, onChange }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");

    // Find name for current symbol
    const currentName = AVAILABLE_SYMBOLS.find(s => s.code === currentSymbol)?.name || currentSymbol;

    const filtered = AVAILABLE_SYMBOLS.filter(s =>
        s.code.includes(searchTerm) || s.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded px-3 py-1.5 transition-all text-xs text-white min-w-[140px] justify-between"
            >
                <div className="flex flex-col items-start">
                    <span className="font-bold">{currentSymbol}</span>
                    <span className="text-[9px] text-gray-400">{currentName}</span>
                </div>
                <div className="bg-blue-500/20 text-blue-300 px-1.5 rounded text-[9px]">KR</div>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        {/* Backdrop to close */}
                        <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="absolute top-full left-0 mt-2 w-64 glass rounded-lg overflow-hidden z-50 flex flex-col"
                        >
                            <div className="p-2 border-b border-white/10">
                                <div className="flex items-center gap-2 bg-black/40 rounded px-2 py-1.5 border border-white/5">
                                    <Search size={12} className="text-gray-500" />
                                    <input
                                        autoFocus
                                        type="text"
                                        className="bg-transparent outline-none text-xs text-white w-full placeholder-gray-600"
                                        placeholder="Search Ticker..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                    />
                                </div>
                            </div>

                            <div className="max-h-60 overflow-y-auto">
                                {filtered.map(s => (
                                    <div
                                        key={s.code}
                                        onClick={() => {
                                            onChange(s.code, s.name);
                                            setIsOpen(false);
                                        }}
                                        className={clsx(
                                            "px-3 py-2 flex items-center justify-between cursor-pointer transition-colors border-l-2 border-transparent",
                                            currentSymbol === s.code
                                                ? "bg-blue-600/20 border-blue-500"
                                                : "hover:bg-white/5 hover:border-white/30"
                                        )}
                                    >
                                        <div>
                                            <div className="text-xs font-bold text-gray-200">{s.code}</div>
                                            <div className="text-[10px] text-gray-400">{s.name}</div>
                                        </div>
                                        <div className="text-[9px] bg-gray-800 text-gray-400 px-1 rounded">{s.type}</div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
};
