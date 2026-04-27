import type {
  Holding,
  HoldingCreate,
  HoldingUpdate,
  PortfolioSummary,
  SellSignal,
  CsvImportResponse,
  AdditionalPurchaseRequest,
  Trade,
  TradeHistoryResponse,
  SellRecordCreate,
  SellRule,
  SellRuleCreate,
  SellRuleType,
  SellRuleUpdate,
  SellRuleEvaluateResult,
  SellRulePreset,
  BulkApplyPresetResponse,
  ArchiveSummary,
  ArchiveDetailResponse,
} from '../types';
import { fetchApi, API_BASE_URL } from './_base';

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
