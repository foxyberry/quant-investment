'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import {
  getBacktestStrategies,
  runBacktest,
  runOptimize,
  type BacktestRequest,
  type OptimizeRequest,
} from '@/lib/api';

export function useBacktestStrategies(enabled: boolean = true) {
  return useQuery({
    queryKey: queryKeys.backtest.strategies(),
    queryFn: getBacktestStrategies,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes - strategies rarely change
  });
}

export function useRunBacktest() {
  return useMutation({
    mutationFn: (request: BacktestRequest) => runBacktest(request),
  });
}

export function useRunOptimize() {
  return useMutation({
    mutationFn: (request: OptimizeRequest) => runOptimize(request),
  });
}
