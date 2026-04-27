import type {
  MacroBundle,
  MacroHistoryResponse,
} from '../types';
import { fetchApi } from './_base';

/**
 * Get macro bundle snapshot (FX + futures + investor flow + regime signal)
 */
export async function getMacroBundle(mode: string = 'kr'): Promise<MacroBundle> {
  return fetchApi<MacroBundle>(`/api/market/macro/bundle?mode=${encodeURIComponent(mode)}`);
}

/**
 * Get macro history for a given window (e.g. 60m, 1d)
 */
export async function getMacroHistory(window: string = '60m'): Promise<MacroHistoryResponse> {
  return fetchApi<MacroHistoryResponse>(`/api/market/macro/history?window=${encodeURIComponent(window)}`);
}

// Sector API types and functions

export interface SectorInfo {
  name: string;
  stock_count: number;
}

export interface SectorListResponse {
  market: string;
  sectors: SectorInfo[];
  total_sectors: number;
}

/**
 * Get available sectors for a given market
 */
export async function getSectors(market: string = 'KOSPI'): Promise<SectorListResponse> {
  return fetchApi<SectorListResponse>(`/api/strategy/sectors?market=${encodeURIComponent(market)}`);
}
