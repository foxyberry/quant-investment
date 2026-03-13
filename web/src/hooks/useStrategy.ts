'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import {
  getStrategyConditions,
  runStrategy,
  listSavedStrategies,
  saveNewStrategy,
  updateSavedStrategy,
  deleteSavedStrategy,
  updateStrategyStatus,
  validateStrategy,
} from '@/lib/api';
import type { StrategyStatus, StrategyValidateRequest } from '@/lib/api';
import type { StrategyGraph } from '@/lib/strategy/graphSerializer';

export function useStrategyConditions() {
  return useQuery({
    queryKey: queryKeys.strategy.conditions(),
    queryFn: getStrategyConditions,
    staleTime: 10 * 60 * 1000, // 10 minutes - conditions rarely change
  });
}

export function useRunStrategy() {
  return useMutation({
    mutationFn: ({
      graph,
      universeOverride,
    }: {
      graph: StrategyGraph;
      universeOverride?: string;
    }) => runStrategy(graph, universeOverride),
  });
}

export function useSavedStrategies() {
  return useQuery({
    queryKey: queryKeys.strategy.saved(),
    queryFn: listSavedStrategies,
  });
}

export function useSaveStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string; graph: StrategyGraph }) =>
      saveNewStrategy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.strategy.saved() });
    },
  });
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: { name?: string; description?: string; graph?: StrategyGraph };
    }) => updateSavedStrategy(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.strategy.saved() });
    },
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSavedStrategy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.strategy.saved() });
    },
  });
}

export function useUpdateStrategyStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: StrategyStatus }) =>
      updateStrategyStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.strategy.saved() });
    },
  });
}

export function useValidateStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      request,
    }: {
      id: string;
      request?: StrategyValidateRequest;
    }) => validateStrategy(id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.strategy.saved() });
    },
  });
}
