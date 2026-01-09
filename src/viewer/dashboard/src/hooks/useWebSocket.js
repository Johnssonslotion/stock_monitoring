import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * 실시간 웹소켓 통신을 위한 커스텀 훅
 * @param {string} url 웹소켓 엔드포인트 URL
 */
export const useWebSocket = (url) => {
    const [data, setData] = useState(null);
    const [status, setStatus] = useState('connecting');
    const ws = useRef(null);

    const connect = useCallback(() => {
        try {
            ws.current = new WebSocket(url);

            ws.current.onopen = () => {
                console.log('WebSocket Connected');
                setStatus('connected');
            };

            ws.current.onmessage = (event) => {
                try {
                    const parsed = JSON.parse(event.data);
                    setData(parsed);
                } catch (e) {
                    setData(event.data);
                }
            };

            ws.current.onclose = () => {
                console.log('WebSocket Disconnected');
                setStatus('disconnected');
                // 5초 후 재연결 시도
                setTimeout(connect, 5000);
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket Error:', error);
                setStatus('error');
            };
        } catch (e) {
            console.error('WebSocket Init Error:', e);
            setStatus('error');
        }
    }, [url]);

    useEffect(() => {
        connect();
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [connect]);

    return { data, status };
};
