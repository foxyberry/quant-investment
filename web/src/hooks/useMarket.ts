'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { getMacroBundle, getMacroHistory, searchTickers } from '@/lib/api';

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
    refetchInterval: 30 * 1000,
    staleTime: 10 * 1000,
  });
}

export function useMacroHistory(window: string = '60m') {
  return useQuery({
    queryKey: queryKeys.market.macroHistory(window),
    queryFn: () => getMacroHistory(window),
    staleTime: 30 * 1000,
  });
}
