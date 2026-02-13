'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { getStrategyConditions, runStrategy } from '@/lib/api';
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
