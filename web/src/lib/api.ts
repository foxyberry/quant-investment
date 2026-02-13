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
  ReportSummary,
  ReportDetail,
  TickerAnalysis,
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

// Strategy API functions

import type { StrategyGraph } from './strategy/graphSerializer';

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

export interface StrategyExecuteResponse {
  results: StrategyResultItem[];
  total_count: number;
  matched_count: number;
  universe: string;
  conditions_used: string[];
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
