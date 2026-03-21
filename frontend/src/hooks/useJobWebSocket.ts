import { useEffect, useRef, useCallback } from 'react';
import type { WSJobUpdate } from '../types';

const WS_BASE =
    (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000')
        .replace(/^http/, 'ws');   // http → ws, https → wss

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1_000;  // 1 s, doubles each attempt, capped at 30 s

interface UseJobWebSocketOptions {
    token: string | null;
    enabled: boolean;
    onUpdate: (update: WSJobUpdate) => void;
}

export function useJobWebSocket({ token, enabled, onUpdate }: UseJobWebSocketOptions): void {
    // Keep a stable reference to the latest callback to avoid stale closures
    const onUpdateRef = useRef(onUpdate);
    useEffect(() => { onUpdateRef.current = onUpdate; }, [onUpdate]);

    const wsRef = useRef<WebSocket | null>(null);
    const retries = useRef(0);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const unmounted = useRef(false);

    const clearTimer = () => {
        if (timerRef.current !== null) {
            clearTimeout(timerRef.current);
            timerRef.current = null;
        }
    };

    const connect = useCallback(() => {
        if (unmounted.current || !token) return;

        const url = `${WS_BASE}/ws?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            retries.current = 0; // reset back-off on successful connection
        };

        ws.onmessage = (event: MessageEvent) => {
            try {
                const data: WSJobUpdate = JSON.parse(event.data as string);
                if (data.event === 'job_update') {
                    onUpdateRef.current(data);
                }
            } catch {
                // ignore malformed messages
            }
        };

        ws.onclose = () => {
            if (unmounted.current) return;
            if (retries.current < MAX_RETRIES) {
                const delay = Math.min(BASE_DELAY_MS * 2 ** retries.current, 30_000);
                retries.current += 1;
                timerRef.current = setTimeout(connect, delay);
            }
        };

        ws.onerror = () => {
            ws.close(); // triggers onclose → reconnect logic
        };
    }, [token]);

    useEffect(() => {
        unmounted.current = false;

        if (!enabled || !token) return;

        connect();

        return () => {
            unmounted.current = true;
            clearTimer();
            wsRef.current?.close();
            wsRef.current = null;
        };
    }, [enabled, token, connect]);
}
