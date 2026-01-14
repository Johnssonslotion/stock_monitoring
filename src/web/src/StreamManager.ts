type MessageHandler = (data: any) => void;

class StreamManager {
    private socket: WebSocket | null = null;
    private handlers: Map<string, Set<MessageHandler>> = new Map();
    private reconnectTimeout: any = null;
    public isConnected: boolean = false;

    constructor() {
        this.connect();
    }

    private connect() {
        // Use relative path for proxy support (ws://host/api/v1/ws)
        // Note: Vite proxy might not handle WS well, direct might be safer if port known
        // But let's try relative first. If fails, fallback to direct port.
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Hardcoded port 8000 for local dev if proxy fails, but try relative /ws first via Vite
        const url = `${protocol}//${window.location.hostname}:8000/ws`;

        console.log(`Connecting to WebSocket: ${url}`);
        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            console.log("WS Connected");
            this.isConnected = true;
        };

        this.socket.onmessage = (event) => {
            try {
                // Redis Pub/Sub messages usually come as stringified JSON
                // Format: { type: 'message', data: "{...}" } or direct data
                // Main.py broadcasts raw strings from Redis
                const raw = event.data;
                const parsed = JSON.parse(raw);

                // Identify message type (Heuristic or strict schema)
                // Market Ticks usually have 'symbol', 'price', 'time'
                if (parsed.price && parsed.volume) {
                    this.emit('tick', parsed);
                }
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };

        this.socket.onclose = () => {
            console.log("WS Closed");
            this.isConnected = false;
            this.scheduleReconnect();
        };

        this.socket.onerror = (err) => {
            console.error("WS Error", err);
            this.socket?.close();
        };
    }

    private scheduleReconnect() {
        if (this.reconnectTimeout) return;
        this.reconnectTimeout = setTimeout(() => {
            this.reconnectTimeout = null;
            this.connect();
        }, 3000);
    }

    public on(event: string, handler: MessageHandler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, new Set());
        }
        this.handlers.get(event)?.add(handler);
    }

    public off(event: string, handler: MessageHandler) {
        this.handlers.get(event)?.delete(handler);
    }

    private emit(event: string, data: any) {
        this.handlers.get(event)?.forEach(h => h(data));
    }
}

export const streamManager = new StreamManager();
