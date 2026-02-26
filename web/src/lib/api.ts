import type {
  PresetInfo,
  UniverseInfo,
  ScreeningResponse,
  ScreeningProgressEvent,
  ScreeningResult,
  SavedScreeningResultSummary,
  SavedScreeningResult,
  Holding,
  HoldingCreate,
  HoldingUpdate,
  PortfolioSummary,
  SellSignal,
  CsvImportResponse,
  ReportSummary,
  ReportDetail,
  TickerAnalysis,
  AIAnalysisResult,
  AnalysisStatus,
  KiwoomConnectionStatus,
  KiwoomConnectionState,
  KiwoomCondition,
  KiwoomConditionMatch,
  KiwoomOrder,
  KiwoomOrderRequest,
  BrokerConnectionStatus,
  BrokerKillSwitchResult,
  BrokerOrder,
  BrokerOrderRequest,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }

  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return response.json();
}

// Screening API functions

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
  params?: Record<string, unknown>
): Promise<ScreeningResponse> {
  return fetchApi<ScreeningResponse>('/api/screening/run', {
    method: 'POST',
    body: JSON.stringify({
      preset,
      universes,
      reference_date: referenceDate ?? null,
      params,
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
  }
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

// Portfolio API functions

/**
 * Get all holdings in the portfolio
 */
export async function getHoldings(): Promise<Holding[]> {
  return fetchApi<Holding[]>('/api/portfolio/holdings');
}

/**
 * Add a new holding to the portfolio
 */
export async function addHolding(data: HoldingCreate): Promise<Holding> {
  return fetchApi<Holding>('/api/portfolio/holdings', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing holding
 */
export async function updateHolding(ticker: string, data: HoldingUpdate): Promise<Holding> {
  return fetchApi<Holding>(`/api/portfolio/holdings/${encodeURIComponent(ticker)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a holding from the portfolio
 */
export async function deleteHolding(ticker: string): Promise<void> {
  return fetchApi<void>(`/api/portfolio/holdings/${encodeURIComponent(ticker)}`, {
    method: 'DELETE',
  });
}

/**
 * Get portfolio summary including total investment, market value, and P&L
 */
export async function getPortfolioSummary(baseCurrency?: string): Promise<PortfolioSummary> {
  const params = baseCurrency ? `?base_currency=${encodeURIComponent(baseCurrency)}` : '';
  return fetchApi<PortfolioSummary>(`/api/portfolio/summary${params}`);
}

/**
 * Get active sell signals (stop loss, take profit, etc.)
 */
export async function getSellSignals(): Promise<SellSignal[]> {
  const response = await fetchApi<{ signals: SellSignal[]; checked_at: string }>('/api/portfolio/sell-signals');
  return response.signals;
}

/**
 * Import holdings from a CSV file
 */
export async function importHoldingsCsv(
  file: File,
  mode: 'merge' | 'replace' = 'merge'
): Promise<CsvImportResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', mode);

  const response = await fetch(`${API_BASE_URL}/api/portfolio/holdings/import`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `API Error: ${response.status}` }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

/**
 * Export holdings as CSV file download
 */
export async function exportHoldingsCsv(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/holdings/export`);
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'portfolio_holdings.csv';
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Download CSV template for portfolio import
 */
export async function downloadHoldingsTemplate(minimal: boolean = false): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/portfolio/holdings/template?minimal=${minimal}`
  );
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = minimal ? 'portfolio_template_minimal.csv' : 'portfolio_template.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// Analysis API functions

/**
 * Get list of recent analysis reports
 */
export async function getReports(limit: number = 10): Promise<ReportSummary[]> {
  const response = await fetchApi<{ reports: ReportSummary[]; total_count: number }>(`/api/analysis/reports?limit=${limit}`);
  return response.reports;
}

/**
 * Get detailed analysis report by date
 */
export async function getReportDetail(date: string, market?: string): Promise<ReportDetail> {
  const params = market ? `?market=${encodeURIComponent(market)}` : '';
  return fetchApi<ReportDetail>(`/api/analysis/reports/${encodeURIComponent(date)}${params}`);
}

/**
 * Get ticker analysis with OHLCV data and technical indicators
 */
export async function getTickerAnalysis(ticker: string, period: string = '6mo'): Promise<TickerAnalysis> {
  return fetchApi<TickerAnalysis>(`/api/analysis/ticker/${encodeURIComponent(ticker)}?period=${period}`);
}

/**
 * Search tickers by name or symbol
 */
export async function searchTickers(query: string): Promise<Array<{ ticker: string; name: string }>> {
  return fetchApi<Array<{ ticker: string; name: string }>>(`/api/search?q=${encodeURIComponent(query)}`);
}

/**
 * Run AI analysis on a stock (Claude API, may take 30+ seconds)
 */
export async function analyzeStock(ticker: string, includeNews = true): Promise<AIAnalysisResult> {
  return fetchApi<AIAnalysisResult>('/api/analysis/analyze', {
    method: 'POST',
    body: JSON.stringify({ ticker, include_news: includeNews }),
  });
}

/**
 * List all saved screening results (summaries only)
 */
export async function listSavedScreeningResults(): Promise<{
  results: SavedScreeningResultSummary[];
  total_count: number;
}> {
  return fetchApi<{ results: SavedScreeningResultSummary[]; total_count: number }>(
    '/api/screening/saved'
  );
}

/**
 * Save a screening result
 */
export async function saveScreeningResult(data: {
  name: string;
  description?: string;
  preset: string;
  universes: string[];
  reference_date?: string | null;
  total_count: number;
  matched_count: number;
  elapsed_ms?: number | null;
  results: ScreeningResult[];
}): Promise<SavedScreeningResult> {
  return fetchApi<SavedScreeningResult>('/api/screening/saved', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Get a single saved screening result (with full results)
 */
export async function getSavedScreeningResult(id: string): Promise<SavedScreeningResult> {
  return fetchApi<SavedScreeningResult>(
    `/api/screening/saved/${encodeURIComponent(id)}`
  );
}

/**
 * Delete a saved screening result
 */
export async function deleteSavedScreeningResult(id: string): Promise<void> {
  return fetchApi<void>(`/api/screening/saved/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

/**
 * Check a single stock against screening conditions
 */
export async function checkStockConditions(
  ticker: string,
  preset = 'accumulation_basic'
): Promise<ScreeningResult> {
  return fetchApi<ScreeningResult>(
    `/api/screening/stock/${encodeURIComponent(ticker)}?preset=${encodeURIComponent(preset)}`
  );
}

/**
 * Get analysis service status (Claude API availability)
 */
export async function getAnalysisStatus(): Promise<AnalysisStatus> {
  return fetchApi<AnalysisStatus>('/api/analysis/status');
}

function normalizeKiwoomStatus(raw: Record<string, unknown>): KiwoomConnectionStatus {
  const rawStatus = typeof raw.status === 'string' ? raw.status.toLowerCase() : '';
  const booleanConnected =
    typeof raw.connected === 'boolean'
      ? raw.connected
      : typeof raw.is_connected === 'boolean'
      ? raw.is_connected
      : null;

  let status: KiwoomConnectionState = 'unavailable';
  if (rawStatus === 'connected' || rawStatus === 'disconnected' || rawStatus === 'connecting') {
    status = rawStatus;
  } else if (booleanConnected === true) {
    status = 'connected';
  } else if (booleanConnected === false) {
    status = 'disconnected';
  }

  const accountsRaw = raw.accounts;
  const accounts = Array.isArray(accountsRaw)
    ? accountsRaw.filter((v): v is string => typeof v === 'string')
    : typeof accountsRaw === 'string'
    ? accountsRaw
        .split(';')
        .map((v) => v.trim())
        .filter((v) => v.length > 0)
    : [];

  return {
    status,
    is_mock_trading:
      typeof raw.is_mock_trading === 'boolean'
        ? raw.is_mock_trading
        : typeof raw.mock_trading === 'boolean'
        ? raw.mock_trading
        : null,
    user_id:
      typeof raw.user_id === 'string'
        ? raw.user_id
        : typeof raw.userId === 'string'
        ? raw.userId
        : null,
    accounts,
    updated_at: typeof raw.updated_at === 'string' ? raw.updated_at : null,
  };
}

export async function getKiwoomConnectionStatus(): Promise<KiwoomConnectionStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/kiwoom/connection/status`);
    if (!response.ok) {
      return {
        status: 'unavailable',
        is_mock_trading: null,
        user_id: null,
        accounts: [],
        updated_at: null,
      };
    }
    const raw = (await response.json()) as Record<string, unknown>;
    const payload =
      raw.data && typeof raw.data === 'object'
        ? (raw.data as Record<string, unknown>)
        : raw;
    return normalizeKiwoomStatus(payload);
  } catch {
    return {
      status: 'unavailable',
      is_mock_trading: null,
      user_id: null,
      accounts: [],
      updated_at: null,
    };
  }
}

export async function getKiwoomConditionList(): Promise<KiwoomCondition[]> {
  const raw = await fetchApi<unknown>('/api/kiwoom/conditions');
  const asRecord = (v: unknown): Record<string, unknown> | null =>
    v && typeof v === 'object' ? (v as Record<string, unknown>) : null;
  const normalize = (item: unknown): KiwoomCondition | null => {
    const record = asRecord(item);
    if (!record) return null;
    const indexRaw = record.index ?? record.condition_index ?? record.id;
    const nameRaw = record.name ?? record.condition_name ?? record.label;
    const index = typeof indexRaw === 'number' ? indexRaw : Number(indexRaw);
    const name = typeof nameRaw === 'string' ? nameRaw : null;
    if (!Number.isFinite(index) || !name) return null;
    return { index, name };
  };

  if (Array.isArray(raw)) {
    return raw.map(normalize).filter((v): v is KiwoomCondition => v !== null);
  }

  const payload = asRecord(raw);
  const listCandidate = payload?.conditions ?? payload?.data;
  if (Array.isArray(listCandidate)) {
    return listCandidate.map(normalize).filter((v): v is KiwoomCondition => v !== null);
  }
  return [];
}

export async function startKiwoomConditionMonitor(condition: KiwoomCondition): Promise<void> {
  await fetchApi('/api/kiwoom/conditions/start', {
    method: 'POST',
    body: JSON.stringify({
      condition_index: condition.index,
      condition_name: condition.name,
    }),
  });
}

export async function stopKiwoomConditionMonitor(condition: KiwoomCondition): Promise<void> {
  await fetchApi('/api/kiwoom/conditions/stop', {
    method: 'POST',
    body: JSON.stringify({
      condition_index: condition.index,
      condition_name: condition.name,
    }),
  });
}

export async function getKiwoomConditionMatches(condition: KiwoomCondition): Promise<KiwoomConditionMatch[]> {
  const raw = await fetchApi<unknown>(
    `/api/kiwoom/conditions/matches?condition_index=${encodeURIComponent(String(condition.index))}&condition_name=${encodeURIComponent(condition.name)}`
  );
  const asRecord = (v: unknown): Record<string, unknown> | null =>
    v && typeof v === 'object' ? (v as Record<string, unknown>) : null;
  const normalize = (item: unknown): KiwoomConditionMatch | null => {
    const record = asRecord(item);
    if (!record) return null;
    const tickerRaw = record.ticker ?? record.code ?? record.symbol;
    const ticker = typeof tickerRaw === 'string' ? tickerRaw : null;
    if (!ticker) return null;
    const priceRaw = record.current_price ?? record.price ?? null;
    const price =
      typeof priceRaw === 'number'
        ? priceRaw
        : typeof priceRaw === 'string'
        ? Number(priceRaw.replace(/,/g, ''))
        : null;
    return {
      ticker,
      name: typeof record.name === 'string' ? record.name : null,
      current_price: Number.isFinite(price as number) ? (price as number) : null,
      updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
    };
  };

  if (Array.isArray(raw)) {
    return raw.map(normalize).filter((v): v is KiwoomConditionMatch => v !== null);
  }
  const payload = asRecord(raw);
  const listCandidate = payload?.matches ?? payload?.stocks ?? payload?.data;
  if (Array.isArray(listCandidate)) {
    return listCandidate.map(normalize).filter((v): v is KiwoomConditionMatch => v !== null);
  }
  return [];
}

function normalizeKiwoomOrder(raw: unknown): KiwoomOrder | null {
  const record = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : null;
  if (!record) return null;

  const orderIdRaw = record.order_id ?? record.order_no ?? record.id;
  const tickerRaw = record.ticker ?? record.code ?? record.symbol;
  const sideRaw = record.side ?? record.order_side ?? 'BUY';
  const orderTypeRaw = record.order_type ?? record.hoga ?? 'LIMIT';
  const statusRaw = record.status ?? record.order_status ?? 'RECEIVED';
  const quantityRaw = record.quantity ?? record.order_qty ?? 0;
  const filledQtyRaw = record.filled_quantity ?? record.executed_qty ?? 0;
  const unfilledQtyRaw = record.unfilled_quantity ?? record.remaining_qty ?? 0;
  const priceRaw = record.price ?? record.order_price ?? null;
  const filledPriceRaw = record.filled_price ?? record.executed_price ?? null;
  const createdAtRaw = record.created_at ?? record.ordered_at ?? new Date().toISOString();

  const toNumber = (value: unknown): number | null => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
      const parsed = Number(value.replace(/,/g, ''));
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  };

  const orderId = typeof orderIdRaw === 'string' ? orderIdRaw : String(orderIdRaw ?? '');
  const ticker = typeof tickerRaw === 'string' ? tickerRaw : '';
  if (!orderId || !ticker) return null;

  const side = sideRaw === 'SELL' ? 'SELL' : 'BUY';
  const orderType = orderTypeRaw === 'MARKET' ? 'MARKET' : 'LIMIT';
  const allowedStatuses = ['RECEIVED', 'CONFIRMED', 'FILLED', 'CANCELED', 'REJECTED', 'PARTIAL'] as const;
  const status = allowedStatuses.includes(statusRaw as (typeof allowedStatuses)[number])
    ? (statusRaw as (typeof allowedStatuses)[number])
    : 'RECEIVED';

  return {
    order_id: orderId,
    ticker,
    side,
    quantity: toNumber(quantityRaw) ?? 0,
    filled_quantity: toNumber(filledQtyRaw) ?? 0,
    unfilled_quantity: toNumber(unfilledQtyRaw) ?? 0,
    order_type: orderType,
    price: toNumber(priceRaw),
    filled_price: toNumber(filledPriceRaw),
    status,
    created_at: typeof createdAtRaw === 'string' ? createdAtRaw : new Date().toISOString(),
    updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
  };
}

export async function placeKiwoomOrder(request: KiwoomOrderRequest): Promise<KiwoomOrder> {
  const raw = await fetchApi<unknown>('/api/kiwoom/orders', {
    method: 'POST',
    body: JSON.stringify(request),
  });
  const normalized = normalizeKiwoomOrder(raw);
  if (!normalized) {
    throw new Error('Invalid order response');
  }
  return normalized;
}

export async function getKiwoomOrders(): Promise<KiwoomOrder[]> {
  const raw = await fetchApi<unknown>('/api/kiwoom/orders');
  const payload = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : null;
  const list = Array.isArray(raw)
    ? raw
    : Array.isArray(payload?.orders)
    ? payload?.orders
    : Array.isArray(payload?.data)
    ? payload?.data
    : [];
  return list.map(normalizeKiwoomOrder).filter((v): v is KiwoomOrder => v !== null);
}

export async function cancelKiwoomOrder(orderId: string): Promise<void> {
  await fetchApi<void>(`/api/kiwoom/orders/${encodeURIComponent(orderId)}/cancel`, {
    method: 'POST',
  });
}

export async function amendKiwoomOrder(
  orderId: string,
  data: { quantity?: number; price?: number | null }
): Promise<void> {
  await fetchApi<void>(`/api/kiwoom/orders/${encodeURIComponent(orderId)}/amend`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function triggerKiwoomKillSwitch(): Promise<void> {
  await fetchApi<void>('/api/kiwoom/orders/kill-switch', {
    method: 'POST',
  });
}

// Unified Broker API functions

export async function listBrokers(): Promise<string[]> {
  const data = await fetchApi<{ brokers: string[] }>('/api/brokers/');
  return data.brokers;
}

export async function getBrokerConnectionStatus(
  broker: string
): Promise<BrokerConnectionStatus> {
  return fetchApi<BrokerConnectionStatus>(
    `/api/brokers/${encodeURIComponent(broker)}/status`
  );
}

export async function placeBrokerOrder(
  broker: string,
  order: BrokerOrderRequest
): Promise<BrokerOrder> {
  return fetchApi<BrokerOrder>(
    `/api/brokers/${encodeURIComponent(broker)}/orders`,
    {
      method: 'POST',
      body: JSON.stringify(order),
    }
  );
}

export async function getBrokerOrders(broker: string): Promise<BrokerOrder[]> {
  return fetchApi<BrokerOrder[]>(
    `/api/brokers/${encodeURIComponent(broker)}/orders`
  );
}

export async function cancelBrokerOrder(
  broker: string,
  orderId: string
): Promise<void> {
  await fetchApi<void>(
    `/api/brokers/${encodeURIComponent(broker)}/orders/${encodeURIComponent(orderId)}`,
    { method: 'DELETE' }
  );
}

export async function amendBrokerOrder(
  broker: string,
  orderId: string,
  amend: { quantity?: number; price?: number | null }
): Promise<void> {
  await fetchApi<void>(
    `/api/brokers/${encodeURIComponent(broker)}/orders/${encodeURIComponent(orderId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(amend),
    }
  );
}

export async function triggerBrokerKillSwitch(
  broker: string
): Promise<BrokerKillSwitchResult> {
  return fetchApi<BrokerKillSwitchResult>(
    `/api/brokers/${encodeURIComponent(broker)}/kill-switch`,
    { method: 'POST' }
  );
}

// Strategy API functions

import type { StrategyGraph } from './strategy/graphSerializer';

// Saved strategy types

export interface SavedStrategy {
  id: string;
  name: string;
  description: string | null;
  graph: StrategyGraph;
  created_at: string;
  updated_at: string;
}

export interface SavedStrategiesListResponse {
  strategies: SavedStrategy[];
  total_count: number;
}

export interface StrategyConditionInfo {
  key: string;
  label: string;
  description: string;
  category: string;
  params: Array<{
    name: string;
    type: string;
    default: unknown;
    description: string;
  }>;
  recommended: boolean;
  order: number;
}

export interface StrategyConditionsResponse {
  conditions: StrategyConditionInfo[];
  categories: string[];
}

export interface StrategyResultItem {
  ticker: string;
  name: string;
  current_price: number | null;
  matched: boolean;
  conditions: Array<Record<string, unknown>>;
}

export interface NodeIntermediateResult {
  node_id: string;
  node_type: string;
  label: string;
  stock_count: number;
  stocks: StrategyResultItem[];
}

export interface StrategyExecuteResponse {
  results: StrategyResultItem[];
  total_count: number;
  matched_count: number;
  universe: string;
  conditions_used: string[];
  node_results: Record<string, NodeIntermediateResult>;
}

export interface StrategyProgressEvent {
  processed_tickers: number;
  total_tickers: number;
  matched_count: number;
  progress_pct: number;
  status: 'running' | 'done' | 'error';
  message?: string;
}

/**
 * Get available strategy conditions
 */
export async function getStrategyConditions(): Promise<StrategyConditionsResponse> {
  return fetchApi<StrategyConditionsResponse>('/api/strategy/conditions');
}

/**
 * Execute a visual strategy graph
 */
export async function runStrategy(
  graph: StrategyGraph,
  universeOverride?: string
): Promise<StrategyExecuteResponse> {
  return fetchApi<StrategyExecuteResponse>('/api/strategy/run', {
    method: 'POST',
    body: JSON.stringify({
      graph,
      universe_override: universeOverride,
    }),
  });
}

/**
 * Execute a visual strategy graph with SSE progress streaming.
 */
export function runStrategyStream(
  graph: StrategyGraph,
  universeOverride?: string,
  callbacks?: {
    onProgress?: (event: StrategyProgressEvent) => void;
    onResult?: (data: StrategyExecuteResponse) => void;
    onError?: (error: string) => void;
  }
): { abort: () => void } {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/strategy/run/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph,
          universe_override: universeOverride,
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
                callbacks?.onProgress?.(parsed as StrategyProgressEvent);
              } else if (currentEvent === 'result') {
                callbacks?.onResult?.(parsed as StrategyExecuteResponse);
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

      // Flush any remaining bytes from the TextDecoder
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
 * List all saved strategies
 */
export async function listSavedStrategies(): Promise<SavedStrategiesListResponse> {
  return fetchApi<SavedStrategiesListResponse>('/api/strategy/saved');
}

/**
 * Save a new strategy
 */
export async function saveNewStrategy(data: {
  name: string;
  description?: string;
  graph: StrategyGraph;
}): Promise<SavedStrategy> {
  return fetchApi<SavedStrategy>('/api/strategy/saved', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing saved strategy
 */
export async function updateSavedStrategy(
  id: string,
  data: { name?: string; description?: string; graph?: StrategyGraph }
): Promise<SavedStrategy> {
  return fetchApi<SavedStrategy>(`/api/strategy/saved/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// Sector API types and functions

export interface SectorInfo {
  name: string;
  stock_count: number;
}

export interface SectorListResponse {
  market: string;
  sectors: SectorInfo[];
  total_sectors: number;
}

/**
 * Get available sectors for a given market
 */
export async function getSectors(market: string = 'KOSPI'): Promise<SectorListResponse> {
  return fetchApi<SectorListResponse>(`/api/strategy/sectors?market=${encodeURIComponent(market)}`);
}

/**
 * Delete a saved strategy
 */
export async function deleteSavedStrategy(id: string): Promise<void> {
  return fetchApi<void>(`/api/strategy/saved/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

// Backtest types

export interface BacktestStrategyParam {
  name: string;
  type: 'int' | 'float' | 'str' | 'bool';
  default: unknown;
  description: string;
}

export interface BacktestStrategy {
  name: string;
  label: string;
  description: string;
  params: BacktestStrategyParam[];
}

export interface BacktestStrategiesResponse {
  strategies: BacktestStrategy[];
}

export interface BacktestRequest {
  ticker: string;
  strategy: string;
  period?: string;
  start_date?: string;
  end_date?: string;
  cash?: number;
  commission?: number;
  strategy_params?: Record<string, unknown>;
}

export interface BacktestMetrics {
  total_return: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  cagr: number;
  num_trades: number;
  avg_trade_return: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
}

export interface BacktestTrade {
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  return_pct: number;
  size: number;
}

export interface EquityPoint {
  date: string;
  equity: number;
}

export interface BacktestResponse {
  metrics: BacktestMetrics;
  trades: BacktestTrade[];
  equity_curve: EquityPoint[];
  ticker: string;
  strategy: string;
  period: string;
}

export interface OptimizeRequest {
  ticker: string;
  strategy: string;
  period?: string;
  cash?: number;
  param_ranges: Record<string, number[]>;
  maximize?: string;
}

export interface OptimizeResponse {
  optimal_params: Record<string, unknown>;
  best_metrics: BacktestMetrics;
}

/**
 * Get available backtest strategies with their parameters
 */
export async function getBacktestStrategies(): Promise<BacktestStrategiesResponse> {
  return fetchApi<BacktestStrategiesResponse>('/api/backtest/strategies');
}

/**
 * Run a backtest with specified strategy and parameters
 */
export async function runBacktest(request: BacktestRequest): Promise<BacktestResponse> {
  return fetchApi<BacktestResponse>('/api/backtest/run', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Optimize strategy parameters for best performance
 */
export async function runOptimize(request: OptimizeRequest): Promise<OptimizeResponse> {
  return fetchApi<OptimizeResponse>('/api/backtest/optimize', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
