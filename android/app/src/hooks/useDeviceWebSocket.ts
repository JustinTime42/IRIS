import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getBaseUrl } from '../shared/config';

/**
 * WebSocket hook for real-time device state updates.
 * Connects to /ws/device-status and invalidates React Query caches when updates arrive.
 */
export function useDeviceWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    const wsUrl = getBaseUrl().replace('http', 'ws') + '/ws/device-status';
    console.debug(`[ws] Connecting to ${wsUrl}`);

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.debug('[ws] Connected');
    };

    ws.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.debug('[ws] Received:', msg.type);

        // Invalidate relevant queries based on update type
        switch (msg.type) {
          case 'door':
            queryClient.invalidateQueries({ queryKey: ['garage', 'door'] });
            break;
          case 'light':
            queryClient.invalidateQueries({ queryKey: ['garage', 'light'] });
            break;
          case 'weather':
            queryClient.invalidateQueries({ queryKey: ['garage', 'weather'] });
            break;
          case 'freezer':
            queryClient.invalidateQueries({ queryKey: ['garage', 'freezer'] });
            break;
          case 'house-monitor':
            queryClient.invalidateQueries({ queryKey: ['house-monitor'] });
            break;
          case 'garage-controller':
            // Garage controller sends consolidated status - invalidate all garage queries
            queryClient.invalidateQueries({ queryKey: ['garage'] });
            break;
          case 'pong':
            // Heartbeat response, ignore
            break;
          default:
            console.debug('[ws] Unknown message type:', msg.type);
        }
      } catch (e) {
        console.warn('[ws] Failed to parse message:', e);
      }
    };

    ws.current.onerror = (error) => {
      console.error('[ws] Error:', error);
    };

    ws.current.onclose = () => {
      console.debug('[ws] Disconnected, reconnecting in 5s...');
      reconnectTimeout.current = setTimeout(connect, 5000);
    };
  }, [queryClient]);

  useEffect(() => {
    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, [connect]);
}
