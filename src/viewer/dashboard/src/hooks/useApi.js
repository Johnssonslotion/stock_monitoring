import { useState, useCallback } from 'react';

/**
 * 인증 처리가 포함된 API 호출을 위한 커스텀 훅
 * @param {string} baseUrl API 서버 기본 URL
 */
export const useApi = (baseUrl) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // 로컬 스토리지 또는 환경변수에서 API Key 획득 (여기선 우선 하드코딩 또는 프롬프트 가능하게 설계)
    const apiKey = localStorage.getItem('ANTIGRAVITY_API_KEY') || 'super-secret-key';

    const request = useCallback(async (endpoint, options = {}) => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${baseUrl}${endpoint}`, {
                ...options,
                headers: {
                    ...options.headers,
                    'X-API-Key': apiKey,
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.statusText}`);
            }

            const data = await response.json();
            setLoading(false);
            return data;
        } catch (err) {
            setError(err.message);
            setLoading(false);
            return null;
        }
    }, [baseUrl, apiKey]);

    return { request, loading, error };
};
