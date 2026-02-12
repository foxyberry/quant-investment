'use client';

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { getReports, getReportDetail, getTickerAnalysis } from '@/lib/api';

export function useReports(limit: number = 10) {
  return useQuery({
    queryKey: queryKeys.analysis.reports(limit),
    queryFn: () => getReports(limit),
  });
}

export function useReportDetail(date: string, market?: string) {
  return useQuery({
    queryKey: queryKeys.analysis.reportDetail(date),
    queryFn: () => getReportDetail(date, market),
    enabled: !!date,
  });
}

export function useTickerAnalysis(ticker: string | null, period: string = '6mo') {
  return useQuery({
    queryKey: queryKeys.analysis.ticker(ticker ?? '', period),
    queryFn: () => getTickerAnalysis(ticker!, period),
    enabled: !!ticker,
  });
}
