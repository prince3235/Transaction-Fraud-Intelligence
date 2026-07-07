import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useStore } from '@/store';
import { PredictionLog } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/alerts';

export function useAlertsSocket() {
  const setWsStatus = useStore((state) => state.setWsStatus);
  const queryClient = useQueryClient();
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const attempts = useRef(0);
  const maxAttempts = 5;

  useEffect(() => {
    let ws: WebSocket;
    let isMounted = true;

    const connect = () => {
      if (attempts.current >= maxAttempts) {
        setWsStatus('disconnected');
        return; // Fallback to polling via React Query
      }

      ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        if (!isMounted) return;
        setWsStatus('connected');
        attempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const newAlert: PredictionLog = JSON.parse(event.data);
          
          // Prepend to React Query cache for alerts
          queryClient.setQueryData(['alerts'], (oldData: PredictionLog[] | undefined) => {
            if (!oldData) return [newAlert];
            return [newAlert, ...oldData];
          });
        } catch (err) {
          console.error("Failed to parse WS message", err);
        }
      };

      ws.onclose = () => {
        if (!isMounted) return;
        setWsStatus('reconnecting');
        
        // Exponential backoff
        const timeout = Math.min(1000 * Math.pow(2, attempts.current), 15000);
        attempts.current += 1;
        
        reconnectTimeout.current = setTimeout(connect, timeout);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws) ws.close();
    };
  }, [setWsStatus, queryClient]);
}
