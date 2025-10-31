'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { EngineCriteria, EngineMessage, RosterResult } from '@/types/roster';

const WS_ENDPOINT = process.env.NEXT_PUBLIC_ROSTER_WS ?? 'ws://localhost:8000/ws/roster';
const REST_ENDPOINT = process.env.NEXT_PUBLIC_ROSTER_REST ?? 'http://localhost:8000/api/solve';

function parseMessage(data: MessageEvent['data']): EngineMessage | null {
  try {
    const parsed = JSON.parse(typeof data === 'string' ? data : data.toString());
    if (parsed && typeof parsed.type === 'string' && 'payload' in parsed) {
      return parsed as EngineMessage;
    }
    return null;
  } catch (error) {
    console.error('Failed to parse engine message', error);
    return null;
  }
}

type EngineState = {
  result: RosterResult | null;
  status: string;
  connected: boolean;
  lastUpdated: string | null;
  errors: string[];
};

export function useRosteringEngine(initialResult?: RosterResult) {
  const [state, setState] = useState<EngineState>({
    result: initialResult ?? null,
    status: 'Idle',
    connected: false,
    lastUpdated: null,
    errors: [],
  });
  const wsRef = useRef<WebSocket | null>(null);
  const criteriaRef = useRef<EngineCriteria | null>(null);

  const closeSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendCriteria = useCallback(
    (payload: EngineCriteria) => {
      criteriaRef.current = payload;
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'criteria', payload } satisfies EngineMessage));
      } else {
        fetch(REST_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
          .then(async (res) => {
            if (!res.ok) {
              throw new Error(`REST request failed with status ${res.status}`);
            }
            const data: RosterResult = await res.json();
            setState((prev) => ({
              ...prev,
              result: data,
              status: 'Result received via REST',
              lastUpdated: new Date().toISOString(),
            }));
          })
          .catch((error) => {
            console.error('REST fallback failed', error);
            setState((prev) => ({
              ...prev,
              status: 'Error sending criteria',
              errors: [...prev.errors, String(error)],
            }));
          });
      }
    },
    []
  );

  useEffect(() => {
    const socket = new WebSocket(WS_ENDPOINT);
    wsRef.current = socket;

    socket.onopen = () => {
      setState((prev) => ({ ...prev, connected: true, status: 'Connected to rostering engine' }));
      if (criteriaRef.current) {
        socket.send(JSON.stringify({ type: 'criteria', payload: criteriaRef.current } satisfies EngineMessage));
      }
    };

    socket.onmessage = (event) => {
      const message = parseMessage(event.data);
      if (!message) return;

      if (message.type === 'result') {
        const result = message.payload as RosterResult;
        setState((prev) => ({
          ...prev,
          result,
          status: 'Live schedule update',
          lastUpdated: new Date().toISOString(),
        }));
      } else if (message.type === 'status') {
        setState((prev) => ({ ...prev, status: String(message.payload) }));
      } else if (message.type === 'error') {
        setState((prev) => ({
          ...prev,
          status: 'Engine error',
          errors: [...prev.errors, String(message.payload)],
        }));
      }
    };

    socket.onerror = (event) => {
      console.error('WebSocket error', event);
      setState((prev) => ({
        ...prev,
        status: 'WebSocket error, using REST fallback',
        connected: false,
      }));
    };

    socket.onclose = () => {
      setState((prev) => ({ ...prev, connected: false, status: 'Disconnected' }));
    };

    return () => {
      closeSocket();
    };
  }, [closeSocket]);

  const clearErrors = useCallback(() => {
    setState((prev) => ({ ...prev, errors: [] }));
  }, []);

  return useMemo(
    () => ({
      ...state,
      sendCriteria,
      clearErrors,
    }),
    [state, sendCriteria, clearErrors]
  );
}
