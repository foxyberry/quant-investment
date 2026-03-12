'use client';

import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { getMacroBundle, getMacroHistory, getOhlcv, searchTickers } from '@/lib/api';

const MACRO_POLL_MS = 30 * 1000; // shared polling cadence for macro queries

export function useSearchTickers(query: string) {
  return useQuery({
    queryKey: queryKeys.market.search(query),
    queryFn: () => searchTickers(query),
    enabled: query.length >= 1,
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useMacroBundle() {
  return useQuery({
    queryKey: queryKeys.market.macroBundle(),
    queryFn: () => getMacroBundle(),
    refetchInterval: MACRO_POLL_MS,
    staleTime: 10 * 1000,
  });
}

const MACRO_HISTORY_STALE_TIME = 2 * 60 * 1000; // 2 minutes

export function useMacroHistory(window: string = '60m', enabled = true) {
  return useQuery({
    queryKey: queryKeys.market.macroHistory(window),
    queryFn: () => getMacroHistory(window),
    refetchInterval: enabled ? MACRO_POLL_MS : false,
    staleTime: MACRO_HISTORY_STALE_TIME,
    placeholderData: (prev) => prev,
    enabled,
  });
}

const ALL_WINDOWS = ['60m', '6h', '1d', '7d', '30d'] as const;

/** Prefetch all macro history windows on mount so tab switches are instant. */
export function usePrefetchMacroHistory(enabled = true) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!enabled) return;
    for (const w of ALL_WINDOWS) {
      void queryClient.prefetchQuery({
        queryKey: queryKeys.market.macroHistory(w),
        queryFn: () => getMacroHistory(w),
        staleTime: MACRO_HISTORY_STALE_TIME,
      });
    }
  }, [queryClient, enabled]);
}

export function useOhlcv(ticker: string, days = 30, enabled = true) {
  return useQuery({
    queryKey: queryKeys.market.ohlcv(ticker, days),
    queryFn: () => getOhlcv(ticker, days),
    staleTime: 60 * 60 * 1000, // 1 hour — daily OHLCV doesn't change often
    enabled: enabled && !!ticker,
  });
}
