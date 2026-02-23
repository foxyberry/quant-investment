'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import {
  getHoldings,
  addHolding,
  updateHolding,
  deleteHolding,
  getPortfolioSummary,
  getSellSignals,
} from '@/lib/api';
import type { HoldingCreate, HoldingUpdate } from '@/lib/types';

export function useHoldings() {
  return useQuery({
    queryKey: queryKeys.portfolio.holdings(),
    queryFn: getHoldings,
  });
}

export function usePortfolioSummary(baseCurrency?: string) {
  return useQuery({
    queryKey: queryKeys.portfolio.summary(baseCurrency),
    queryFn: () => getPortfolioSummary(baseCurrency),
  });
}

export function useSellSignals() {
  return useQuery({
    queryKey: queryKeys.portfolio.sellSignals(),
    queryFn: getSellSignals,
  });
}

export function useAddHolding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: HoldingCreate) => addHolding(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.portfolio.all });
    },
  });
}

export function useUpdateHolding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticker, data }: { ticker: string; data: HoldingUpdate }) =>
      updateHolding(ticker, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.portfolio.all });
    },
  });
}

export function useDeleteHolding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticker: string) => deleteHolding(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.portfolio.all });
    },
  });
}
