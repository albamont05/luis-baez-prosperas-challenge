import { useEffect, useRef, useCallback } from 'react';
import type { WSJobUpdate } from '../types';

// Mejoramos la conversión de protocolos para soportar HTTPS -> WSS en AWS
const getWsBase = () => {
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
    return apiBase.replace(/^http/, 'ws');
};

const WS_BASE = getWsBase();
const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1_000;

interface UseJobWebSocketOptions {
    token: string | null;
    enabled: boolean;
    onUpdate: (update: WSJobUpdate) => void;
}

export function useJobWebSocket({ token, enabled, onUpdate }: UseJobWebSocketOptions): void {
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

        // Construcción limpia de la URL
        const url = `${WS_BASE}/ws?token=${encodeURIComponent(token)}`;
        console.log("Intentando conectar WebSocket a:", url);

        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WebSocket conectado con éxito");
            retries.current = 0;
        };

        ws.onmessage = (event: MessageEvent) => {
            try {
                const data = JSON.parse(event.data as string);

                // Verificamos que sea el evento correcto
                if (data.event === 'job_update') {
                    // Pasamos el objeto completo (incluyendo download_url y result_url)
                    onUpdateRef.current(data as WSJobUpdate);
                }
            } catch (err) {
                console.error("Error parseando mensaje WS:", err);
            }
        };

        ws.onclose = (e) => {
            if (unmounted.current) return;

            console.warn(`WebSocket cerrado (Código: ${e.code}). Reintentando...`);

            if (retries.current < MAX_RETRIES) {
                const delay = Math.min(BASE_DELAY_MS * 2 ** retries.current, 30_000);
                retries.current += 1;
                timerRef.current = setTimeout(connect, delay);
            }
        };

        ws.onerror = (err) => {
            console.error("Error en WebSocket:", err);
            ws.close();
        };
    }, [token]);

    useEffect(() => {
        unmounted.current = false;

        if (!enabled || !token) return;

        connect();

        return () => {
            unmounted.current = true;
            clearTimer();
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [enabled, token, connect]);
}