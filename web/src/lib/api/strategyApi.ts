import type {
  ExecutionHistoryListResponse,
  ExecutionHistoryDetail,
  DuplicateCheckResponse,
} from '../types';
import type { StrategyGraph } from '../strategy/graphSerializer';
import { fetchApi, API_BASE_URL } from './_base';

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
