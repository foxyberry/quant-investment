import type {
  PresetInfo,
  UniverseInfo,
  ScreeningResponse,
  ScreeningProgressEvent,
  ScreeningResult,
} from '../types';
import { fetchApi, API_BASE_URL } from './_base';

/**
 * Get available screening presets
 */
export async function getPresets(): Promise<PresetInfo[]> {
  return fetchApi<PresetInfo[]>('/api/screening/presets');
}

/**
 * Get available stock universes
 */
export async function getUniverses(): Promise<UniverseInfo[]> {
  return fetchApi<UniverseInfo[]>('/api/screening/universes');
}

/**
 * Run screening with specified preset and universes
 */
export async function runScreening(
  preset: string,
  universes: string[],
  referenceDate?: string | null,
  params?: Record<string, unknown>,
  graph?: Record<string, unknown> | null,
): Promise<ScreeningResponse> {
  return fetchApi<ScreeningResponse>('/api/screening/run', {
    method: 'POST',
    body: JSON.stringify({
      preset,
      universes,
      reference_date: referenceDate ?? null,
      params,
      ...(graph ? { graph } : {}),
    }),
  });
}

/**
 * Run screening with SSE progress streaming.
 */
export function runScreeningStream(
  preset: string,
  universes: string[],
  referenceDate?: string | null,
  params?: Record<string, unknown>,
  callbacks?: {
    onProgress?: (event: ScreeningProgressEvent) => void;
    onResult?: (data: ScreeningResponse) => void;
    onError?: (error: string) => void;
  },
  graph?: Record<string, unknown> | null,
): { abort: () => void } {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/screening/run/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset,
          universes,
          universe: universes[0] ?? 'KOSPI',
          reference_date: referenceDate ?? null,
          params,
          ...(graph ? { graph } : {}),
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        callbacks?.onError?.(`API Error: ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks?.onError?.('No response body');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';

      const processLines = (lines: string[]) => {
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              if (currentEvent === 'progress') {
                callbacks?.onProgress?.(parsed as ScreeningProgressEvent);
              } else if (currentEvent === 'result') {
                callbacks?.onResult?.(parsed as ScreeningResponse);
              } else if (currentEvent === 'error') {
                callbacks?.onError?.(parsed.message || 'Unknown error');
              }
            } catch {
              // Ignore parse errors for heartbeats etc.
            }
            currentEvent = '';
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        processLines(lines);
      }

      buffer += decoder.decode(new Uint8Array(), { stream: false });
      if (buffer.trim()) {
        processLines(buffer.split('\n'));
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      callbacks?.onError?.(err instanceof Error ? err.message : 'Stream failed');
    }
  })();

  return { abort: () => controller.abort() };
}

/**
 * Check a single stock against a preset
 */
export async function checkStock(
  ticker: string,
  preset: string
): Promise<ScreeningResult> {
  return fetchApi<ScreeningResult>(`/api/screening/check/${ticker}?preset=${encodeURIComponent(preset)}`);
}
