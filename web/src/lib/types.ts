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
