export const API_BASE = '/api/v1';

export async function fetchJson<T>(endpoint: string): Promise<T | null> {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'x-api-key': 'super-secret-key', // Local API Key (matches API_AUTH_SECRET)
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            console.warn(`API Error ${endpoint}: ${response.status} ${response.statusText}`);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error(`Network Error ${endpoint}:`, error);
        return null;
    }
}
