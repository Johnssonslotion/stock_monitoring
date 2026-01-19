export const API_BASE = '/api/v1';
export const VIRTUAL_API_BASE = '/api/virtual';

export async function fetchJson<T>(endpoint: string, base: string = API_BASE): Promise<T | null> {
    try {
        const url = endpoint.startsWith('/') ? `${base}${endpoint}` : `${base}/${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'x-api-key': 'super-secret-key',
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            console.warn(`API Error ${url}: ${response.status} ${response.statusText}`);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error(`Network Error ${endpoint}:`, error);
        return null;
    }
}

export async function postJson<T>(endpoint: string, body: any, base: string = API_BASE): Promise<T | null> {
    try {
        const url = endpoint.startsWith('/') ? `${base}${endpoint}` : `${base}/${endpoint}`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'x-api-key': 'super-secret-key',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.warn(`API POST Error ${url}: ${response.status}`, errorData);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error(`Network POST Error ${endpoint}:`, error);
        return null;
    }
}
