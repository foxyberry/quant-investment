'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { getTickerAnalysis } from '@/lib/api';

export function useTickerAnalysis(ticker: string | null, period: string = '6mo') {
  return useQuery({
    queryKey: queryKeys.analysis.ticker(ticker ?? '', period),
    queryFn: () => getTickerAnalysis(ticker!, period),
    enabled: !!ticker,
  });
}
