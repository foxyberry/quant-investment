import type {
  PresetInfo,
  UniverseInfo,
  ScreeningResponse,
  ScreeningProgressEvent,
  ScreeningResult,
  ExecutionHistoryListResponse,
  ExecutionHistoryDetail,
  DuplicateCheckResponse,
  AdditionalPurchaseRequest,
  Holding,
  HoldingCreate,
  HoldingUpdate,
  PortfolioSummary,
  SellSignal,
  CsvImportResponse,
  TickerAnalysis,
  AIAnalysisResult,
  AnalysisStatus,
  MacroBundle,
  MacroHistoryResponse,
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
  TigerSettings,
  TigerSettingsUpsert,
  IBKRSettings,
  IBKRSettingsUpsert,
  TelegramSettings,
  TelegramSettingsUpsert,
  TelegramTestResult,
  Trade,
  TradeHistoryResponse,
  SellRecordCreate,
  WatchlistItem,
  WatchlistItemCreate,
  WatchlistItemUpdate,
  BuyRule,
  BuyRuleCreate,
  BuyRuleUpdate,
  BuyRuleTemplate,
  BuySignal,
  BulkApplyPresetResponse,
  SellRule,
  SellRuleCreate,
  SellRuleType,
  SellRuleUpdate,
  SellRuleEvaluateResult,
  SellRulePreset,
  OHLCVData,
  ArchiveSummary,
  ArchiveDetailResponse,
  ReportSummary,
  ReportDetail,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body.detail || body.message || '';
    } catch { /* ignore parse errors */ }
    throw new Error(detail || `API Error: ${response.status}`);
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
    let detail = '';
    try {
      const body = await response.json();
      detail = body.detail || body.message || '';
    } catch { /* ignore parse errors */ }
    throw new Error(detail || `API Error: ${response.status}`);
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
 * Record an additional purchase for an existing holding
 */
export async function addPurchase(ticker: string, data: AdditionalPurchaseRequest): Promise<Holding> {
  return fetchApi<Holding>(`/api/portfolio/holdings/${encodeURIComponent(ticker)}/add-purchase`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Record a sell transaction
 */
export async function recordSell(data: SellRecordCreate): Promise<Trade> {
  return fetchApi<Trade>('/api/portfolio/trades', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Get trade history, optionally filtered by ticker
 */
export async function getTradeHistory(ticker?: string): Promise<TradeHistoryResponse> {
  const params = ticker ? `?ticker=${encodeURIComponent(ticker)}` : '';
  return fetchApi<TradeHistoryResponse>(`/api/portfolio/trades${params}`);
}

// Sell Rule API functions

export async function getSellRules(ticker: string): Promise<SellRule[]> {
  return fetchApi<SellRule[]>(`/api/portfolio/holdings/${encodeURIComponent(ticker)}/sell-rules`);
}

export async function createSellRule(ticker: string, data: SellRuleCreate): Promise<SellRule> {
  return fetchApi<SellRule>(`/api/portfolio/holdings/${encodeURIComponent(ticker)}/sell-rules`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateSellRule(ruleId: number, data: SellRuleUpdate): Promise<SellRule> {
  return fetchApi<SellRule>(`/api/portfolio/sell-rules/${ruleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteSellRule(ruleId: number): Promise<void> {
  return fetchApi<void>(`/api/portfolio/sell-rules/${ruleId}`, {
    method: 'DELETE',
  });
}

export async function evaluateSellRules(ticker?: string): Promise<{ results: SellRuleEvaluateResult[]; checked_at: string }> {
  const params = ticker ? `?ticker=${encodeURIComponent(ticker)}` : '';
  return fetchApi<{ results: SellRuleEvaluateResult[]; checked_at: string }>(`/api/portfolio/sell-rules/evaluate${params}`, {
    method: 'POST',
  });
}

// Sell Rule Preset API functions

export async function getSellRulePresets(): Promise<SellRulePreset[]> {
  return fetchApi<SellRulePreset[]>('/api/portfolio/sell-rule-presets');
}

export async function createSellRulePreset(data: {
  name: string;
  description?: string;
  rules: Array<{ rule_type: SellRuleType; params: Record<string, unknown> }>;
}): Promise<SellRulePreset> {
  return fetchApi<SellRulePreset>('/api/portfolio/sell-rule-presets', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function applySellRulePreset(ticker: string, presetId: number): Promise<SellRule[]> {
  return fetchApi<SellRule[]>(
    `/api/portfolio/holdings/${encodeURIComponent(ticker)}/sell-rules/from-preset`,
    {
      method: 'POST',
      body: JSON.stringify({ preset_id: presetId }),
    }
  );
}

export async function saveAsPreset(
  ticker: string,
  name: string,
  description?: string
): Promise<SellRulePreset> {
  return fetchApi<SellRulePreset>(
    `/api/portfolio/holdings/${encodeURIComponent(ticker)}/sell-rules/save-as-preset`,
    {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }
  );
}

export async function bulkApplyPreset(presetId: number, tickers: string[]): Promise<BulkApplyPresetResponse> {
  return fetchApi<BulkApplyPresetResponse>(
    `/api/portfolio/sell-rule-presets/${presetId}/bulk-apply`,
    {
      method: 'POST',
      body: JSON.stringify({ tickers }),
    }
  );
}

/**
 * Download CSV template for portfolio import
 */
export async function downloadHoldingsTemplate(minimal: boolean = false): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/portfolio/holdings/template?minimal=${minimal}`
  );
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body.detail || body.message || '';
    } catch { /* ignore parse errors */ }
    throw new Error(detail || `API Error: ${response.status}`);
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
 * Get ticker analysis with OHLCV data and technical indicators
 */
export async function getTickerAnalysis(ticker: string, period: string = '6mo', includeNews = false): Promise<TickerAnalysis> {
  const params = new URLSearchParams({ period });
  if (includeNews) params.set('include_news', 'true');
  return fetchApi<TickerAnalysis>(`/api/analysis/ticker/${encodeURIComponent(ticker)}?${params.toString()}`);
}

/**
 * Search tickers by name or symbol
 */
export async function searchTickers(query: string): Promise<Array<{ ticker: string; name: string }>> {
  return fetchApi<Array<{ ticker: string; name: string }>>(`/api/search?q=${encodeURIComponent(query)}`);
}

/**
 * Get macro bundle snapshot (FX + futures + investor flow + regime signal)
 */
export async function getMacroBundle(mode: string = 'kr'): Promise<MacroBundle> {
  return fetchApi<MacroBundle>(`/api/market/macro/bundle?mode=${encodeURIComponent(mode)}`);
}

/**
 * Get macro history for a given window (e.g. 60m, 1d)
 */
export async function getMacroHistory(window: string = '60m'): Promise<MacroHistoryResponse> {
  return fetchApi<MacroHistoryResponse>(`/api/market/macro/history?window=${encodeURIComponent(window)}`);
}

/**
 * Get OHLCV data for a ticker
 */
export async function getOhlcv(ticker: string, days = 30): Promise<{ ticker: string; data: OHLCVData[]; period_days: number }> {
  const raw = await fetchApi<{ ticker: string; data: Array<{ date: string; open: number; high: number; low: number; close: number; volume: number }>; period_days: number }>(
    `/api/market/ohlcv/${encodeURIComponent(ticker)}?days=${days}`
  );
  return {
    ...raw,
    data: raw.data.map((d) => ({ time: d.date, open: d.open, high: d.high, low: d.low, close: d.close, volume: d.volume })),
  };
}

/**
 * Get current price for a single ticker
 */
export async function getTickerPrice(ticker: string): Promise<{ ticker: string; price: number | null }> {
  return fetchApi<{ ticker: string; price: number | null }>(`/api/price/${encodeURIComponent(ticker)}`);
}

/**
 * Run AI analysis on a stock (Claude API, may take 30+ seconds)
 */
export async function analyzeStock(ticker: string, includeNews = true, locale?: string): Promise<AIAnalysisResult> {
  return fetchApi<AIAnalysisResult>('/api/analysis/analyze', {
    method: 'POST',
    body: JSON.stringify({ ticker, include_news: includeNews, locale }),
  });
}

// --- Execution History API ---

/**
 * List execution history with optional filtering
 */
export async function getExecutions(
  options?: { execution_type?: string; limit?: number; offset?: number }
): Promise<ExecutionHistoryListResponse> {
  const params = new URLSearchParams();
  if (options?.execution_type) params.set('execution_type', options.execution_type);
  if (options?.limit) params.set('limit', String(options.limit));
  if (options?.offset) params.set('offset', String(options.offset));
  const qs = params.toString();
  return fetchApi<ExecutionHistoryListResponse>(
    `/api/reports/executions${qs ? `?${qs}` : ''}`
  );
}

/**
 * Get a single execution history detail
 */
export async function getExecution(id: string): Promise<ExecutionHistoryDetail> {
  return fetchApi<ExecutionHistoryDetail>(
    `/api/reports/executions/${encodeURIComponent(id)}`
  );
}

/**
 * Update an execution (e.g., rename)
 */
export async function updateExecution(
  id: string,
  data: { name: string },
): Promise<ExecutionHistoryDetail> {
  return fetchApi<ExecutionHistoryDetail>(
    `/api/reports/executions/${encodeURIComponent(id)}`,
    { method: 'PATCH', body: JSON.stringify(data) },
  );
}

/**
 * Save an execution result to history
 */
export async function saveExecution(data: {
  execution_type: 'screening' | 'strategy';
  preset: string;
  universes: string[];
  reference_date?: string | null;
  params?: Record<string, unknown> | null;
  graph?: Record<string, unknown> | null;
  total_count: number;
  matched_count: number;
  elapsed_ms?: number | null;
  results: Array<Record<string, unknown>>;
  name?: string | null;
  description?: string | null;
  strategy_id?: string | null;
}): Promise<ExecutionHistoryDetail> {
  return fetchApi<ExecutionHistoryDetail>('/api/reports/executions', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Check if a duplicate execution exists
 */
export async function checkDuplicateExecution(
  executionType: string,
  preset: string,
  universes: string[],
  referenceDate?: string | null
): Promise<DuplicateCheckResponse> {
  const params = new URLSearchParams({
    execution_type: executionType,
    preset,
    universes: universes.join(','),
  });
  if (referenceDate) params.set('reference_date', referenceDate);
  return fetchApi<DuplicateCheckResponse>(
    `/api/reports/executions/check-duplicate?${params.toString()}`
  );
}

/**
 * Delete an execution history record
 */
export async function deleteExecution(id: string): Promise<void> {
  return fetchApi<void>(`/api/reports/executions/${encodeURIComponent(id)}`, {
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

export async function getSettingsBrokerStatuses(): Promise<BrokerConnectionStatus[]> {
  const data = await fetchApi<{ brokers: BrokerConnectionStatus[] }>('/api/settings/brokers');
  return data.brokers;
}

export async function getTigerSettings(): Promise<TigerSettings> {
  return fetchApi<TigerSettings>('/api/settings/brokers/tiger');
}

export async function saveTigerSettings(payload: TigerSettingsUpsert): Promise<TigerSettings> {
  return fetchApi<TigerSettings>('/api/settings/brokers/tiger', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testTigerConnection(): Promise<BrokerConnectionStatus> {
  return fetchApi<BrokerConnectionStatus>('/api/settings/brokers/tiger/test', {
    method: 'POST',
  });
}

export async function getIbkrSettings(): Promise<IBKRSettings> {
  return fetchApi<IBKRSettings>('/api/settings/brokers/ibkr');
}

export async function saveIbkrSettings(payload: IBKRSettingsUpsert): Promise<IBKRSettings> {
  return fetchApi<IBKRSettings>('/api/settings/brokers/ibkr', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testIbkrConnection(): Promise<BrokerConnectionStatus> {
  return fetchApi<BrokerConnectionStatus>('/api/settings/brokers/ibkr/test', {
    method: 'POST',
  });
}

export async function getTelegramSettings(): Promise<TelegramSettings> {
  return fetchApi<TelegramSettings>('/api/settings/telegram');
}

export async function saveTelegramSettings(payload: TelegramSettingsUpsert): Promise<TelegramSettings> {
  return fetchApi<TelegramSettings>('/api/settings/telegram', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testTelegramNotification(): Promise<TelegramTestResult> {
  return fetchApi<TelegramTestResult>('/api/settings/telegram/test', {
    method: 'POST',
  });
}

// Slack notification settings

export interface SlackSettings {
  has_webhook_url: boolean;
  channel_name: string | null;
  enabled: boolean;
  updated_at: string | null;
}

export interface SlackSettingsUpsert {
  webhook_url?: string;
  channel_name?: string;
  enabled: boolean;
}

export interface SlackTestResult {
  success: boolean;
  message: string;
}

export async function getSlackSettings(): Promise<SlackSettings> {
  return fetchApi<SlackSettings>('/api/settings/slack');
}

export async function saveSlackSettings(payload: SlackSettingsUpsert): Promise<SlackSettings> {
  return fetchApi<SlackSettings>('/api/settings/slack', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testSlackNotification(): Promise<SlackTestResult> {
  return fetchApi<SlackTestResult>('/api/settings/slack/test', {
    method: 'POST',
  });
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

// Watchlist API functions

export async function getWatchlistItems(): Promise<WatchlistItem[]> {
  return fetchApi<WatchlistItem[]>('/api/watchlist/items');
}

export async function getWatchlistItem(itemId: number): Promise<WatchlistItem> {
  return fetchApi<WatchlistItem>(`/api/watchlist/items/${itemId}`);
}

export async function createWatchlistItem(data: WatchlistItemCreate): Promise<WatchlistItem> {
  return fetchApi<WatchlistItem>('/api/watchlist/items', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateWatchlistItem(itemId: number, data: WatchlistItemUpdate): Promise<WatchlistItem> {
  return fetchApi<WatchlistItem>(`/api/watchlist/items/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteWatchlistItem(itemId: number): Promise<void> {
  return fetchApi<void>(`/api/watchlist/items/${itemId}`, {
    method: 'DELETE',
  });
}

export async function getBuyRules(itemId: number): Promise<BuyRule[]> {
  return fetchApi<BuyRule[]>(`/api/watchlist/items/${itemId}/buy-rules`);
}

export async function createBuyRule(itemId: number, data: BuyRuleCreate): Promise<BuyRule> {
  return fetchApi<BuyRule>(`/api/watchlist/items/${itemId}/buy-rules`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateBuyRule(ruleId: number, data: BuyRuleUpdate): Promise<BuyRule> {
  return fetchApi<BuyRule>(`/api/watchlist/buy-rules/${ruleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteBuyRule(ruleId: number): Promise<void> {
  return fetchApi<void>(`/api/watchlist/buy-rules/${ruleId}`, {
    method: 'DELETE',
  });
}

// Buy Rule Template API
export async function getBuyRuleTemplates(): Promise<BuyRuleTemplate[]> {
  return fetchApi<BuyRuleTemplate[]>('/api/watchlist/buy-rule-templates');
}

export async function createRuleFromTemplate(itemId: number, templateId: number): Promise<BuyRule> {
  return fetchApi<BuyRule>(`/api/watchlist/items/${itemId}/buy-rules/from-template`, {
    method: 'POST',
    body: JSON.stringify({ template_id: templateId }),
  });
}

export async function getBuySignals(): Promise<BuySignal[]> {
  const response = await fetchApi<{ signals: BuySignal[]; checked_at: string }>('/api/watchlist/buy-signals');
  return response.signals;
}

// Strategy API functions

import type { StrategyGraph } from './strategy/graphSerializer';

// Saved strategy types

export type StrategyStatus = 'draft' | 'backtested' | 'validated' | 'production' | 'retired';

export interface SavedStrategy {
  id: string;
  name: string;
  description: string | null;
  graph: StrategyGraph;
  status: StrategyStatus;
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
  market?: string | null;
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
  universes?: string[];
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

/**
 * Update the lifecycle status of a saved strategy
 */
export async function updateStrategyStatus(
  id: string,
  status: StrategyStatus
): Promise<SavedStrategy> {
  return fetchApi<SavedStrategy>(
    `/api/strategy/saved/${encodeURIComponent(id)}/status`,
    {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }
  );
}

// Strategy validation types

export interface StrategyValidateRequest {
  ticker?: string;
  period?: string;
}

export interface IndicatorComparison {
  name: string;
  our_value: number | null;
  reference_value: number | null;
  difference: number | null;
  pct_difference: number | null;
  match: boolean;
  note: string | null;
}

export interface StrategyValidateResponse {
  strategy_id: string;
  indicators_tested: string[];
  comparisons: IndicatorComparison[];
  all_pass: boolean;
  status_before: string;
  status_after: string;
  message: string;
}

/**
 * Validate a strategy's indicators via cross-validation
 */
export async function validateStrategy(
  id: string,
  request: StrategyValidateRequest = {}
): Promise<StrategyValidateResponse> {
  return fetchApi<StrategyValidateResponse>(
    `/api/strategy/saved/${encodeURIComponent(id)}/validate`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    }
  );
}

// Strategy comparison types

export interface StrategyMetricsSummary {
  strategy_id: string;
  strategy_name: string;
  status: string;
  ticker: string;
  period: string;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  cagr: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  total_return: number | null;
  profit_factor: number | null;
  total_trades: number;
  avg_trade_return: number | null;
  backtested_at: string | null;
}

export interface StrategyCompareResponse {
  strategies: StrategyMetricsSummary[];
  best_sharpe: string | null;
  best_cagr: string | null;
  best_win_rate: string | null;
  lowest_drawdown: string | null;
}

export interface LeaderboardEntry {
  rank: number;
  strategy_id: string;
  strategy_name: string;
  status: string;
  sharpe_ratio: number | null;
  cagr: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  total_return: number | null;
  total_trades: number;
  backtested_at: string | null;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  sort_by: string;
  order: string;
  total_count: number;
}

/**
 * Compare 2-4 strategies side by side
 */
export async function compareStrategies(
  strategyIds: string[]
): Promise<StrategyCompareResponse> {
  return fetchApi<StrategyCompareResponse>('/api/strategy/compare', {
    method: 'POST',
    body: JSON.stringify({ strategy_ids: strategyIds }),
  });
}

/**
 * Get strategy leaderboard
 */
export async function getLeaderboard(params?: {
  sort_by?: string;
  order?: string;
  status?: string;
  limit?: number;
}): Promise<LeaderboardResponse> {
  const searchParams = new URLSearchParams();
  if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
  if (params?.order) searchParams.set('order', params.order);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  const qs = searchParams.toString();
  return fetchApi<LeaderboardResponse>(`/api/strategy/leaderboard${qs ? `?${qs}` : ''}`);
}

// Pine Script export

export interface PineScriptExportRequest {
  graph: StrategyGraph;
  strategy_name?: string;
  take_profit?: number;
  stop_loss?: number;
}

export interface PineScriptExportResponse {
  pine_script: string;
  strategy_name: string;
  conditions_used: string[];
  conditions_skipped: string[];
}

export async function exportPineScript(
  data: PineScriptExportRequest
): Promise<PineScriptExportResponse> {
  return fetchApi<PineScriptExportResponse>('/api/strategy/export/pine-script', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Graph backtest types

export interface GraphBacktestRequest {
  graph: StrategyGraph;
  ticker: string;
  strategy_id?: string;
  period?: string;
  start?: string;
  end?: string;
  cash?: number;
  commission?: number;
  take_profit?: number;
  stop_loss?: number;
  include_trades?: boolean;
  include_equity_curve?: boolean;
}

export interface GraphBacktestResponse {
  ticker: string;
  strategy: string;
  period: string;
  cash: number;
  metrics: BacktestMetrics;
  trades: BacktestTrade[];
  equity_curve: EquityPoint[];
  compiled_conditions: string[];
  skipped_conditions: string[];
  warnings: string[];
  strategy_status?: string | null;
}

/**
 * Run a backtest using a strategy graph
 */
export async function runGraphBacktest(
  request: GraphBacktestRequest
): Promise<GraphBacktestResponse> {
  return fetchApi<GraphBacktestResponse>('/api/backtest/run-graph', {
    method: 'POST',
    body: JSON.stringify(request),
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

// ── Portfolio Archives ──────────────────────────────────────────────────────

/**
 * Create a new portfolio archive (snapshot of current holdings)
 */
export async function createPortfolioArchive(data: { name: string; description?: string; clear_after?: boolean }): Promise<ArchiveDetailResponse> {
  return fetchApi<ArchiveDetailResponse>('/api/portfolio/archives', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * List all portfolio archives
 */
export async function listPortfolioArchives(): Promise<ArchiveSummary[]> {
  return fetchApi<ArchiveSummary[]>('/api/portfolio/archives');
}

/**
 * Get a single portfolio archive by ID
 */
export async function getPortfolioArchive(id: number, withPrices = false): Promise<ArchiveDetailResponse> {
  return fetchApi<ArchiveDetailResponse>(`/api/portfolio/archives/${id}?with_prices=${withPrices}`);
}

/**
 * Delete a portfolio archive by ID
 */
export async function deletePortfolioArchive(id: number): Promise<void> {
  return fetchApi<void>(`/api/portfolio/archives/${id}`, { method: 'DELETE' });
}

export async function clearPortfolioCache(): Promise<void> {
  return fetchApi<void>('/api/portfolio/cache/clear', { method: 'POST' });
}

export async function deleteAllHoldings(): Promise<void> {
  return fetchApi<void>('/api/portfolio/holdings', { method: 'DELETE' });
}

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
