import type {
  ReportSummary,
  ReportDetail,
} from '../types';
import { fetchApi, API_BASE_URL } from './_base';

// ── Portfolio AI Chat ────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatStreamEvent {
  type: string;
  content?: string;
  name?: string;
  input?: unknown;
  message?: string;
}

// ── Daily Portfolio Report API ────────────────────────────────────────────────

export async function listReports(limit = 30): Promise<ReportSummary[]> {
  return fetchApi<ReportSummary[]>(`/api/portfolio/report/?limit=${limit}`);
}

export async function getLatestReport(): Promise<ReportDetail | null> {
  try {
    return await fetchApi<ReportDetail>('/api/portfolio/report/latest');
  } catch (e: unknown) {
    if (e instanceof Error && e.message.includes('404')) return null;
    throw e;
  }
}

export async function getReport(id: number): Promise<ReportDetail | null> {
  try {
    return await fetchApi<ReportDetail>(`/api/portfolio/report/${id}`);
  } catch (e: unknown) {
    if (e instanceof Error && e.message.includes('404')) return null;
    throw e;
  }
}

/**
 * SSE streaming alternative to generateReportBackground.
 * Not used by the current UI (which uses background + polling), but kept for
 * future use if we want to switch to an inline streaming experience.
 */
export async function* streamGenerateReport(signal?: AbortSignal): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch(`${API_BASE_URL}/api/portfolio/report/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
  });
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string'
        ? body.detail
        : JSON.stringify(body.detail ?? '');
    } catch { /* ignore */ }
    throw new Error(detail || `Report error: ${res.status}`);
  }
  if (!res.body) throw new Error('No response body from report endpoint');
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6)) as ChatStreamEvent;
        } catch { /* skip malformed events */ }
      }
    }
  }
}

export async function sendReportToSlack(id: number): Promise<boolean> {
  const result = await fetchApi<{ success: boolean }>(`/api/portfolio/report/${id}/slack`, { method: 'POST' });
  return result.success;
}

export async function generateReportBackground(): Promise<{ started: boolean; already_running: boolean }> {
  return fetchApi('/api/portfolio/report/generate-background', { method: 'POST' });
}

export async function getReportStatus(): Promise<{ is_generating: boolean }> {
  return fetchApi('/api/portfolio/report/status');
}

/**
 * Stream portfolio AI chat responses via SSE.
 * Yields parsed event objects until the stream ends.
 * Pass an AbortSignal to cancel mid-stream (e.g. when the panel closes).
 */
export async function* streamPortfolioChat(
  messages: ChatMessage[],
  includePortfolio = true,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch(`${API_BASE_URL}/api/chat/portfolio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, include_portfolio: includePortfolio }),
    signal,
  });
  if (!res.ok) {
    // Surface server-side detail — detail may be a string (HTTPException) or
    // an array of objects (Pydantic 422), so always stringify it.
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string'
        ? body.detail
        : JSON.stringify(body.detail ?? '');
    } catch { /* ignore */ }
    throw new Error(detail || `Chat error: ${res.status}`);
  }
  if (!res.body) throw new Error('No response body from chat endpoint');
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6)) as ChatStreamEvent;
        } catch { /* skip malformed events */ }
      }
    }
  }
}
