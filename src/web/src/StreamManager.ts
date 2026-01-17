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
        // Priority: 1. Full URL (Env) 2. Port (Env) 3. Default (8000)
        const envUrl = import.meta.env.VITE_API_URL;
        let url: string;

        if (envUrl) {
            url = envUrl; // e.g., "ws://remote-ip:8000/ws"
        } else {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const port = import.meta.env.VITE_API_PORT || 8000;
            url = `${protocol}//${window.location.hostname}:${port}/ws`;
        }

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

                // Strict Schema Validation (Spec Compliance)
                // Use 'type' field to distinguish messages
                if (parsed.type === 'tick') {
                    this.emit('tick', parsed);
                } else if (parsed.type === 'orderbook') {
                    this.emit('orderbook', parsed);
                } else if (parsed.price && parsed.volume) {
                    // Fallback for legacy messages (during migration)
                    console.warn("Received legacy packet without type field");
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
