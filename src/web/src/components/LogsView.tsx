import React from 'react';
import axios from 'axios';
import { DataGrid } from './DataGrid';
import { streamManager } from '../StreamManager';

export const LogsView: React.FC = () => {
    const [logs, setLogs] = React.useState<any[]>([]);

    React.useEffect(() => {
        // Initial Fetch for history
        const fetchHistory = async () => {
            try {
                const res = await axios.get('/inspector/latest?limit=50');
                setLogs(res.data);
            } catch (e) { console.error(e); }
        };
        fetchHistory();

        // Subscribe to real-time updates
        const handleTick = (newTick: any) => {
            setLogs(prev => {
                const updated = [newTick, ...prev];
                return updated.slice(0, 50); // Keep latest 50
            });
        };

        streamManager.on('tick', handleTick);
        return () => streamManager.off('tick', handleTick);
    }, []);

    return (
        <div className="flex flex-col h-full">
            {/* Header removed as it's now in App.tsx container for Glassmorphism consistency */}
            <div className="flex-1 overflow-auto">
                <DataGrid data={logs} />
            </div>
        </div>
    );
};
