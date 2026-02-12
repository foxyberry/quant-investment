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
  return fetchApi<SellSignal[]>('/api/portfolio/sell-signals');
}

// Analysis API functions

/**
 * Get list of recent analysis reports
 */
export async function getReports(limit: number = 10): Promise<ReportSummary[]> {
  return fetchApi<ReportSummary[]>(`/api/analysis/reports?limit=${limit}`);
}
