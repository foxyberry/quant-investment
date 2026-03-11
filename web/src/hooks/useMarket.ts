'use client';

import { useQuery } from '@tanstack/react-query';
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

export function useMacroHistory(window: string = '60m') {
  return useQuery({
    queryKey: queryKeys.market.macroHistory(window),
    queryFn: () => getMacroHistory(window),
    refetchInterval: MACRO_POLL_MS,
    staleTime: MACRO_POLL_MS,
    placeholderData: (prev) => prev,
  });
}

export function useOhlcv(ticker: string, days = 30) {
  return useQuery({
    queryKey: queryKeys.market.ohlcv(ticker, days),
    queryFn: () => getOhlcv(ticker, days),
    staleTime: 60 * 60 * 1000, // 1 hour — daily OHLCV doesn't change often
    enabled: !!ticker,
  });
}
