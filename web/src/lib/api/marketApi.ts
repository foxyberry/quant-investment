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

// ---------------------------------------------------------------------------
// Worldmonitor endpoints
// ---------------------------------------------------------------------------

export interface MarketRadarExchange {
  name: string | null;
  country: string | null;
  index: string | null;
  value: number | null;
  change_pct: number | null;
  status: string | null;
}

export interface MarketRadarResponse {
  exchanges: MarketRadarExchange[];
  commodities: Record<string, unknown> | null;
  crypto: Record<string, unknown> | null;
  updated_at: string | null;
  available: boolean;
}

export interface CountryRiskSignal {
  category: string;
  score: number | null;
  trend: string | null;
}

export interface CountryRiskResponse {
  country_code: string;
  country_name: string | null;
  overall_score: number | null;
  risk_level: string | null;
  signals: CountryRiskSignal[];
  updated_at: string | null;
  available: boolean;
}

export interface GlobalBriefItem {
  domain: string | null;
  headline: string | null;
  summary: string | null;
  severity: string | null;
  region: string | null;
}

export interface GlobalBriefResponse {
  items: GlobalBriefItem[];
  generated_at: string | null;
  available: boolean;
}

export async function getMarketRadar(): Promise<MarketRadarResponse> {
  return fetchApi<MarketRadarResponse>('/api/market/macro/market-radar');
}

export async function getCountryRisk(countryCode: string): Promise<CountryRiskResponse> {
  return fetchApi<CountryRiskResponse>(`/api/market/macro/country-risk/${encodeURIComponent(countryCode)}`);
}

export async function getGlobalBrief(): Promise<GlobalBriefResponse> {
  return fetchApi<GlobalBriefResponse>('/api/market/macro/global-brief');
}
