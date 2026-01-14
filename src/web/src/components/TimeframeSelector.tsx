import React from 'react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';

export type Timeframe = '1m' | '5m' | '1d';

interface TimeframeSelectorProps {
    selected: Timeframe;
    onChange: (interval: Timeframe) => void;
}

export const TimeframeSelector: React.FC<TimeframeSelectorProps> = ({ selected, onChange }) => {
    const options: { label: string; value: Timeframe }[] = [
        { label: '1M', value: '1m' },
        { label: '5M', value: '5m' },
        { label: '1D', value: '1d' },
    ];

    return (
        <div className="flex items-center bg-black/40 rounded-lg p-1 border border-white/5 backdrop-blur-md">
            {options.map((option) => (
                <button
                    key={option.value}
                    onClick={() => onChange(option.value)}
                    className={clsx(
                        "relative px-2.5 py-1 text-[10px] font-bold rounded-md transition-all z-10",
                        selected === option.value
                            ? "text-white"
                            : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                    )}
                >
                    {selected === option.value && (
                        <motion.div
                            layoutId="timeframe-active"
                            className="absolute inset-0 bg-blue-600 rounded-md shadow-lg shadow-blue-500/20"
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            style={{ zIndex: -1 }}
                        />
                    )}
                    {option.label}
                </button>
            ))}
        </div>
    );
};
