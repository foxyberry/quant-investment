import type {
  TickerAnalysis,
  AIAnalysisResult,
  AnalysisStatus,
  OHLCVData,
  ScreeningResult,
  WatchlistItem,
  WatchlistItemCreate,
  WatchlistItemUpdate,
  BuyRule,
  BuyRuleCreate,
  BuyRuleUpdate,
  BuyRuleTemplate,
  BuySignal,
} from '../types';
import { fetchApi } from './_base';

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
