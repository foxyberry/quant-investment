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

// Screening types
export interface PresetInfo {
  name: string;
  description: string;
  conditions: string[];
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
}

export interface SellSignal {
  ticker: string;
  name: string | null;
  signal_type: 'stop_loss' | 'take_profit' | 'trailing_stop' | 'manual';
  reason: string;
  current_price: number | null;
  trigger_price: number | null;
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
    sector: string;
  };
}
