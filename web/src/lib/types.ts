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
