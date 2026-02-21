import type {
  PresetInfo,
  UniverseInfo,
  ScreeningResponse,
  ScreeningResult,
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
 * Run screening with specified preset and universe
 */
export async function runScreening(
  preset: string,
  universe: string,
  params?: Record<string, unknown>
): Promise<ScreeningResponse> {
  return fetchApi<ScreeningResponse>('/api/screening/run', {
    method: 'POST',
    body: JSON.stringify({
      preset,
      universe,
      params,
    }),
  });
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
export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  return fetchApi<PortfolioSummary>('/api/portfolio/summary');
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

      // Process any remaining data in buffer after stream closes
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
