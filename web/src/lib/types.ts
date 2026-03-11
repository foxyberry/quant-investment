// API Response wrapper
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  meta?: {
    timestamp: string;
    processing_time_ms?: number;
  };
}

// Health check
export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
}

export type KiwoomConnectionState = 'connected' | 'disconnected' | 'connecting' | 'unavailable';

export interface KiwoomConnectionStatus {
  status: KiwoomConnectionState;
  is_mock_trading: boolean | null;
  user_id: string | null;
  accounts: string[];
  updated_at: string | null;
}

// Screening types
export interface PresetInfo {
  name: string;
  description: string;
  conditions: string[];
  source: 'static' | 'custom' | 'sample';
}

export interface UniverseInfo {
  name: string;
  description: string;
  stock_count: number;
}

export interface ConditionResult {
  condition_name: string;
  matched: boolean;
  details: Record<string, unknown>;
}

export interface ScreeningResult {
  ticker: string;
  name: string;
  current_price: number | null;
  market?: string | null;
  change_pct?: number | null;
  volume?: number | null;
  score?: number | null;
  matched: boolean;
  conditions: ConditionResult[];
}

export interface ScreeningResponse {
  results: ScreeningResult[];
  total_count: number;
  matched_count: number;
  universes?: string[];
  reference_date?: string | null;
  elapsed_ms?: number | null;
}

export interface ScreeningProgressEvent {
  processed_tickers: number;
  total_tickers: number;
  matched_count: number;
  progress_pct: number;
  status: 'running' | 'done' | 'error';
  message?: string;
}

export interface KiwoomCondition {
  index: number;
  name: string;
}

export type KiwoomConditionSignalType = 'I' | 'D';

export interface KiwoomConditionEvent {
  type: KiwoomConditionSignalType;
  ticker: string;
  name?: string | null;
  price?: number | null;
  occurred_at: string;
}

export interface KiwoomConditionMatch {
  ticker: string;
  name?: string | null;
  current_price?: number | null;
  updated_at?: string | null;
}

export type KiwoomOrderSide = 'BUY' | 'SELL';
export type KiwoomOrderType = 'MARKET' | 'LIMIT';
export type KiwoomOrderStatus = 'RECEIVED' | 'CONFIRMED' | 'FILLED' | 'CANCELED' | 'REJECTED' | 'PARTIAL';

export interface KiwoomOrderRequest {
  ticker: string;
  side: KiwoomOrderSide;
  quantity: number;
  order_type: KiwoomOrderType;
  price?: number | null;
}

export interface KiwoomOrder {
  order_id: string;
  ticker: string;
  side: KiwoomOrderSide;
  quantity: number;
  filled_quantity: number;
  unfilled_quantity: number;
  order_type: KiwoomOrderType;
  price: number | null;
  filled_price: number | null;
  status: KiwoomOrderStatus;
  created_at: string;
  updated_at?: string | null;
}

// Portfolio types
export interface Holding {
  ticker: string;
  name: string | null;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  change_pct: number | null;
  market_value: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  currency: string;
  sector: string | null;
}

export interface HoldingCreate {
  ticker: string;
  quantity: number;
  avg_price: number;
  currency?: string;
}

export interface HoldingUpdate {
  quantity?: number;
  avg_price?: number;
}

export interface PortfolioSummary {
  total_investment: number;
  total_market_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  holdings_count: number;
  currency: string;
  cash_balance?: number | null;
  available_cash?: number | null;
}

export interface SellSignal {
  ticker: string;
  name: string | null;
  signal_type: 'stop_loss' | 'take_profit' | 'trailing_stop' | 'holding_period' | 'manual';
  reason: string;
  current_price: number | null;
  trigger_price: number | null;
  avg_price: number;
  pnl_pct: number;
  currency: string;
  rule_id: number | null;
}

// CSV import types
export interface CsvRowError {
  row: number;
  ticker: string | null;
  reason: string;
}

export interface CsvImportResponse {
  imported: number;
  updated: number;
  skipped: number;
  errors: CsvRowError[];
}

// OHLCV data for charts
export interface OHLCVData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

// Technical indicators data
export interface TechnicalIndicators {
  rsi?: {
    value: number;
    signal: 'oversold' | 'neutral' | 'overbought';
  };
  macd?: {
    macd: number;
    signal: number;
    histogram: number;
    prev_histogram?: number | null;
    trend: 'bullish' | 'neutral' | 'bearish';
    cross?: 'bullish' | 'bearish' | 'none';
  };
  bollingerBands?: {
    upper: number;
    middle: number;
    lower: number;
    position: 'above' | 'within' | 'below';
  };
  sma?: {
    sma20: number;
    sma50: number;
    sma200: number;
  };
  stochastic?: {
    k: number;
    d: number | null;
  };
  obv?: {
    value: number;
    trend: 'rising' | 'falling' | 'flat';
  };
  volume?: {
    current: number;
    average: number;
    ratio: number;
  };
}

// Ticker analysis response
export interface NewsArticle {
  title: string;
  source: string;
  date: string;
  summary: string;
  sentiment: string;
  url: string;
}

export interface TickerAnalysis {
  ticker: string;
  name: string;
  current_price: number;
  change_pct: number;
  timestamp?: string;
  ohlcv: OHLCVData[];
  technical: TechnicalIndicators;
  fundamental?: {
    market_cap: number;
    pe_ratio: number | null;
    forward_pe?: number | null;
    pb_ratio?: number | null;
    ps_ratio?: number | null;
    peg_ratio?: number | null;
    dividend_yield: number | null;
    eps: number | null;
    revenue?: number | null;
    revenue_growth?: number | null;
    profit_margin?: number | null;
    roe?: number | null;
    roa?: number | null;
    debt_to_equity?: number | null;
    current_ratio?: number | null;
    enterprise_value?: number | null;
    sector: string;
    industry?: string | null;
    description?: string | null;
    week52_high?: number | null;
    week52_low?: number | null;
  };
  news?: {
    articles: NewsArticle[];
    sentiment_summary: string;
  };
}

// AI Analysis result
export interface AIAnalysisResult {
  ticker: string;
  name: string;
  current_price: number;
  valuation_score: number;
  risk_score: number;
  entry_recommendation: 'BUY' | 'WAIT' | 'AVOID';
  reasoning: string;
  key_risks: string[];
  catalysts: string[];
}

// Analysis service status
export interface AnalysisStatus {
  ai_available: boolean;
  provider: 'anthropic' | 'openai' | null;
  claude_available: boolean; // backward compat
  cache_available: boolean;
  enrichers: {
    technical: boolean;
    fundamental: boolean;
    news: boolean;
  };
  data_dir: string | null;
}

// Macro monitoring types (FX + futures + investor flow)
export type MacroRegime = 'risk_on' | 'neutral' | 'risk_off' | 'unknown';

export interface MacroFxSnapshot {
  pair: string; // e.g. USD/KRW
  value: number | null;
  change_pct: number | null;
  updated_at: string | null;
}

export interface MacroFuturesSnapshot {
  symbol: string; // e.g. KOSPI200_FUT
  value: number | null;
  basis: number | null;
  change_pct: number | null;
  updated_at: string | null;
}

export type FlowAlignment = 'aligned_buy' | 'aligned_sell' | 'foreign_lead' | 'institution_lead' | 'unknown';
export type FlowStrength = 'strong' | 'moderate' | 'weak';

export interface MacroInvestorFlowSnapshot {
  market: string; // e.g. KOSPI
  foreign_net: number | null;
  institution_net: number | null;
  individual_net: number | null;
  window_min: number | null;
  updated_at: string | null;
  alignment?: FlowAlignment | null;
  foreign_strength?: FlowStrength | null;
  kosdaq_foreign_net?: number | null;
  kosdaq_institution_net?: number | null;
  kosdaq_individual_net?: number | null;
}

export interface MacroSignalComponent {
  raw: number;
  decay: number;
  weight: number;
  contribution: number;
  half_life_sec?: number | null;
}

export interface MacroReasonDetail {
  version: number;
  summary: string;
  components: {
    fx: MacroSignalComponent;
    futures: MacroSignalComponent;
    flow: MacroSignalComponent;
  };
}

export interface MacroSignal {
  macro_score: number | null;
  regime: MacroRegime;
  reason: string | null;
  reason_detail?: MacroReasonDetail | null;
  updated_at: string | null;
}

export interface MacroFreshness {
  fx_age_sec: number | null;
  futures_age_sec: number | null;
  flow_age_sec: number | null;
}

export interface MacroVolatilitySnapshot {
  vix: number | null;
  vix_change_pct: number | null;
  vix_as_of: string | null;
  vkospi: number | null;
  vkospi_change_pct: number | null;
  vkospi_as_of: string | null;
  fear_greed: string | null;
  vkospi_vix_ratio: number | null;
}

export interface MacroQuotePoint {
  value: number | null;
  change_pct: number | null;
  as_of: string | null;
}

export interface MacroGlobalSnapshot {
  dxy: MacroQuotePoint | null;
  wti: MacroQuotePoint | null;
  gold: MacroQuotePoint | null;
  copper: MacroQuotePoint | null;
  msci_em: MacroQuotePoint | null;
  msci_dm: MacroQuotePoint | null;
  em_dm_ratio: number | null;
  copper_gold_ratio: number | null;
}

export type MacroEntrySignal = 'buy_favorable' | 'wait' | 'caution';

export interface MacroInterpretation {
  entry_signal: MacroEntrySignal;
  fx_interpretation: string;
  futures_interpretation: string;
  flow_interpretation: string;
}

export interface MacroBreadthSnapshot {
  market: string | null;
  advancing: number | null;
  declining: number | null;
  unchanged: number | null;
  total: number | null;
  ad_ratio: number | null;
  updated_at: string | null;
}

export interface MacroEvent {
  date: string;
  type: string;
  title_key: string;
  importance: string | null;
  d_day: number;
}

export interface MacroBundle {
  fx: MacroFxSnapshot;
  futures: MacroFuturesSnapshot;
  flow: MacroInvestorFlowSnapshot;
  signal: MacroSignal;
  freshness: MacroFreshness;
  bonds?: MacroBondSnapshot | null;
  volatility?: MacroVolatilitySnapshot | null;
  global_macro?: MacroGlobalSnapshot | null;
  breadth?: MacroBreadthSnapshot | null;
  events?: MacroEvent[] | null;
  interpretation?: MacroInterpretation | null;
  cache_hit?: boolean | null;
  generated_at?: string | null;
  is_market_hours?: boolean | null;
}

export interface MacroBondSnapshot {
  us_10y: number | null;
  us_2y: number | null;
  us_spread_2_10: number | null;
  inverted: boolean | null;
  kr_10y: number | null;
  kr_3y: number | null;
  kr_us_spread_10y: number | null;
  source_updated_at: string | null;
  stale: boolean | null;
}

export interface MacroHistoryPoint {
  timestamp: string;
  fx_value: number | null;
  futures_value: number | null;
  foreign_net: number | null;
  macro_score: number | null;
  regime: MacroRegime;
}

export interface MacroHistoryResponse {
  window: string;
  points: MacroHistoryPoint[];
}

// Broker-agnostic types (unified broker router)
export type BrokerOrderSide = 'BUY' | 'SELL';
export type BrokerOrderType = 'MARKET' | 'LIMIT';
export type BrokerOrderStatus =
  | 'RECEIVED'
  | 'CONFIRMED'
  | 'PARTIAL'
  | 'FILLED'
  | 'CANCELED'
  | 'REJECTED';
export type BrokerConnectionState =
  | 'connected'
  | 'disconnected'
  | 'connecting'
  | 'unavailable';

export interface BrokerOrderRequest {
  ticker: string;
  side: BrokerOrderSide;
  quantity: number;
  order_type: BrokerOrderType;
  price?: number | null;
  account_id?: string | null;
}

export interface BrokerOrder {
  order_id: string;
  broker: string;
  ticker: string;
  side: BrokerOrderSide;
  quantity: number;
  filled_quantity: number;
  unfilled_quantity: number;
  order_type: BrokerOrderType;
  price: number | null;
  filled_price: number | null;
  status: BrokerOrderStatus;
  created_at: string;
  updated_at?: string | null;
}

export interface BrokerConnectionStatus {
  broker: string;
  status: BrokerConnectionState;
  is_paper_trading: boolean | null;
  accounts: string[];
  updated_at: string | null;
}

export interface BrokerKillSwitchResult {
  activated: boolean;
  cancelled_orders: number;
}

export interface TigerSettings {
  tiger_id: string | null;
  account: string | null;
  license: string | null;
  sandbox: boolean;
  has_private_key: boolean;
  updated_at: string | null;
}

export interface TigerSettingsUpsert {
  tiger_id: string;
  account: string;
  private_key?: string | null;
  license: string;
  sandbox: boolean;
}

export interface IBKRSettings {
  gateway_url: string | null;
  account_id: string | null;
  updated_at: string | null;
}

export interface IBKRSettingsUpsert {
  gateway_url: string;
  account_id?: string | null;
}

// Execution history types
export interface ExecutionHistorySummary {
  id: string;
  execution_type: 'screening' | 'strategy';
  preset: string;
  universes: string[];
  reference_date?: string | null;
  total_count: number;
  matched_count: number;
  elapsed_ms?: number | null;
  name?: string | null;
  description?: string | null;
  strategy_id?: string | null;
  created_at: string;
}

export interface ExecutionHistoryDetail extends ExecutionHistorySummary {
  results: Array<Record<string, unknown>>;
}

export interface ExecutionHistoryListResponse {
  items: ExecutionHistorySummary[];
  total_count: number;
}

export interface DuplicateCheckResponse {
  exists: boolean;
  existing_id?: string | null;
  created_at?: string | null;
}

// Trade / sell recording types
export interface Trade {
  id: number;
  ticker: string;
  name: string | null;
  trade_type: string;
  quantity: number;
  price: number;
  fee: number;
  tax: number;
  realized_pnl: number | null;
  avg_price_at_trade: number | null;
  currency: string;
  note: string | null;
  traded_at: string;
  created_at: string;
}

export interface TradeHistoryResponse {
  trades: Trade[];
  total_realized_pnl: number;
  trade_count: number;
}

export interface AdditionalPurchaseRequest {
  quantity: number;
  price: number;
  fee?: number;
  traded_at?: string; // YYYY-MM-DD
  note?: string;
}

export interface SellRecordCreate {
  ticker: string;
  quantity: number;
  price: number;
  fee?: number;
  tax?: number;
  traded_at: string; // YYYY-MM-DD
  note?: string;
}

// Sell rule types
export type SellRuleType = 'stop_loss' | 'take_profit' | 'trailing_stop' | 'holding_period';

export interface SellRule {
  id: number;
  ticker: string;
  rule_type: SellRuleType;
  params: Record<string, unknown>;
  state_json: Record<string, unknown> | null;
  preset_id: number | null;
  is_active: boolean;
  triggered_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SellRuleCreate {
  rule_type: SellRuleType;
  params: Record<string, unknown>;
  is_active?: boolean;
}

export interface SellRuleUpdate {
  params?: Record<string, unknown>;
  is_active?: boolean;
}

export interface SellRulePresetItem {
  rule_type: SellRuleType;
  params: Record<string, unknown>;
}

export interface SellRulePreset {
  id: number;
  name: string;
  description: string | null;
  rules: SellRulePresetItem[];
  is_active: boolean;
  linked_rules_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface SellRuleEvaluateResult {
  rule_id: number;
  ticker: string;
  rule_type: string;
  triggered: boolean;
  reason: string | null;
  current_price: number | null;
  trigger_value: number | null;
}

// Bulk apply preset types
export interface BulkApplyResultItem {
  ticker: string;
  success: boolean;
  rules_created: number;
  error: string | null;
}

export interface BulkApplyPresetResponse {
  preset_id: number;
  total: number;
  succeeded: number;
  failed: number;
  results: BulkApplyResultItem[];
}

// Watchlist types
export interface WatchlistItem {
  id: number;
  ticker: string;
  name: string | null;
  target_price: number | null;
  current_price: number | null;
  change_pct: number | null;
  currency: string | null;
  note: string | null;
  tags: string[] | null;
  buy_rules_count: number;
  added_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface WatchlistItemCreate {
  ticker: string;
  name?: string;
  target_price?: number;
  note?: string;
  tags?: string[];
}

export interface WatchlistItemUpdate {
  name?: string;
  target_price?: number | null;
  note?: string;
  tags?: string[];
}

export type BuyRuleType = 'target_price' | 'rsi_oversold';

export interface BuyRule {
  id: number;
  watchlist_item_id: number;
  template_id: number | null;
  rule_type: BuyRuleType;
  params: Record<string, unknown>;
  state_json: Record<string, unknown> | null;
  is_active: boolean;
  triggered_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface BuyRuleTemplate {
  id: number;
  name: string;
  rule_type: BuyRuleType;
  params: Record<string, unknown>;
  description: string | null;
  is_active: boolean;
  linked_rules_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface BuyRuleCreate {
  rule_type: BuyRuleType;
  params: Record<string, unknown>;
  is_active?: boolean;
}

export interface BuyRuleUpdate {
  params?: Record<string, unknown>;
  is_active?: boolean;
}

export interface BuySignal {
  ticker: string;
  name: string | null;
  signal_type: string;
  reason: string;
  current_price: number | null;
  target_price: number | null;
  currency: string | null;
  rule_id: number | null;
}
