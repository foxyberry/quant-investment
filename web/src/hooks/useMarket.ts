'use client';

import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import {
  getMacroBundle,
  getMacroHistory,
  getOhlcv,
  searchTickers,
  getMarketRadar,
  getCountryRisk,
  getGlobalBrief,
} from '@/lib/api';

const MACRO_POLL_MS = 30 * 1000; // shared polling cadence for macro queries

export function useSearchTickers(query: string) {
  return useQuery({
    queryKey: queryKeys.market.search(query),
    queryFn: () => searchTickers(query),
    enabled: query.length >= 1,
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useMacroBundle(mode: string = 'kr') {
  return useQuery({
    queryKey: queryKeys.market.macroBundle(mode),
    queryFn: () => getMacroBundle(mode),
    refetchInterval: MACRO_POLL_MS,
    staleTime: 10 * 1000,
  });
}

// Window-specific staleTime and refetchInterval (ms)
const WINDOW_STALE_TIME: Record<string, number> = {
  '60m': 30 * 1000,       // 30s — fast-changing
  '6h': 2 * 60 * 1000,    // 2min
  '1d': 2 * 60 * 1000,    // 2min
  '7d': 10 * 60 * 1000,   // 10min — slow-changing
  '30d': 10 * 60 * 1000,  // 10min
};

const WINDOW_REFETCH: Record<string, number> = {
  '60m': 30 * 1000,
  '6h': 60 * 1000,
  '1d': 60 * 1000,
  '7d': 5 * 60 * 1000,
  '30d': 5 * 60 * 1000,
};

export function useMacroHistory(window: string = '60m', enabled = true) {
  const staleTime = WINDOW_STALE_TIME[window] ?? 2 * 60 * 1000;
  const refetchInterval = WINDOW_REFETCH[window] ?? MACRO_POLL_MS;
  return useQuery({
    queryKey: queryKeys.market.macroHistory(window),
    queryFn: () => getMacroHistory(window),
    refetchInterval: enabled ? refetchInterval : false,
    staleTime,
    placeholderData: (prev) => prev,
    enabled,
  });
}

// Adjacent windows to prefetch (current ± 1)
const ADJACENT: Record<string, readonly string[]> = {
  '60m': ['6h'],
  '6h': ['60m', '1d'],
  '1d': ['6h', '7d'],
  '7d': ['1d', '30d'],
  '30d': ['7d'],
};

/** Prefetch adjacent macro history windows for instant tab switches. */
export function usePrefetchMacroHistory(enabled = true, currentWindow: string = '60m') {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!enabled) return;
    const adjacent = ADJACENT[currentWindow] ?? [];
    for (const w of adjacent) {
      const staleTime = WINDOW_STALE_TIME[w] ?? 2 * 60 * 1000;
      void queryClient.prefetchQuery({
        queryKey: queryKeys.market.macroHistory(w),
        queryFn: () => getMacroHistory(w),
        staleTime,
      });
    }
  }, [queryClient, enabled, currentWindow]);
}

export function useOhlcv(ticker: string, days = 30, enabled = true) {
  return useQuery({
    queryKey: queryKeys.market.ohlcv(ticker, days),
    queryFn: () => getOhlcv(ticker, days),
    staleTime: 60 * 60 * 1000, // 1 hour — daily OHLCV doesn't change often
    enabled: enabled && !!ticker,
  });
}

// ---------------------------------------------------------------------------
// Worldmonitor hooks
// ---------------------------------------------------------------------------

export function useMarketRadar(enabled = true) {
  return useQuery({
    queryKey: queryKeys.market.marketRadar(),
    queryFn: getMarketRadar,
    staleTime: 5 * 60 * 1000, // 5 min
    refetchInterval: enabled ? 5 * 60 * 1000 : false,
    enabled,
  });
}

export function useCountryRisk(countryCode: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.market.countryRisk(countryCode),
    queryFn: () => getCountryRisk(countryCode),
    staleTime: 10 * 60 * 1000, // 10 min
    enabled: enabled && !!countryCode,
  });
}

export function useGlobalBrief(enabled = true) {
  return useQuery({
    queryKey: queryKeys.market.globalBrief(),
    queryFn: getGlobalBrief,
    staleTime: 5 * 60 * 1000, // 5 min
    enabled,
  });
}
