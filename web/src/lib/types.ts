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
  source: 'static' | 'custom';
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
  matched: boolean;
  conditions: ConditionResult[];
}

export interface ScreeningResponse {
  results: ScreeningResult[];
  total_count: number;
  matched_count: number;
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
  market_value: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  currency: string;
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
  signal_type: 'stop_loss' | 'take_profit' | 'trailing_stop' | 'manual';
  reason: string;
  current_price: number | null;
  trigger_price: number | null;
  avg_price: number;
  pnl_pct: number;
  currency: string;
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

// Analysis types
export interface ReportSummary {
  date: string;
  market: string;
  total_stocks: number;
  buy_count: number;
  wait_count: number;
  avoid_count: number;
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
    trend: 'bullish' | 'neutral' | 'bearish';
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
  volume?: {
    current: number;
    average: number;
    ratio: number;
  };
}

// Report detail with markdown content
export interface ReportDetail {
  date: string;
  market: string;
  content: string;
  stocks: Array<Record<string, unknown>>;
}

// Ticker analysis response
export interface TickerAnalysis {
  ticker: string;
  name: string;
  current_price: number;
  change_pct: number;
  ohlcv: OHLCVData[];
  technical: TechnicalIndicators;
  fundamental?: {
    market_cap: number;
    pe_ratio: number | null;
    dividend_yield: number | null;
    eps: number | null;
    sector: string;
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
  claude_available: boolean;
  cache_available: boolean;
  enrichers: {
    technical: boolean;
    fundamental: boolean;
    news: boolean;
  };
  data_dir: string | null;
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
