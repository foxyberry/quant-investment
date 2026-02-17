'use client';

import { createContext, useContext, useMemo } from 'react';
import { useStrategyConditions } from '@/hooks/useStrategy';
import type { StrategyConditionInfo } from '@/lib/api';

interface ConditionsContextValue {
  conditions: StrategyConditionInfo[];
  categories: string[];
  isLoading: boolean;
  error: Error | null;
  getConditionMeta: (key: string) => StrategyConditionInfo | undefined;
  getConditionsByCategory: () => Record<string, StrategyConditionInfo[]>;
  getDefaultParams: (key: string) => Record<string, unknown>;
}

const ConditionsContext = createContext<ConditionsContextValue | null>(null);

export function ConditionsProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading, error } = useStrategyConditions();

  const value = useMemo<ConditionsContextValue>(() => {
    const conditions = data?.conditions ?? [];
    const categories = data?.categories ?? [];

    const conditionMap = new Map<string, StrategyConditionInfo>();
    for (const c of conditions) {
      conditionMap.set(c.key, c);
    }

    return {
      conditions,
      categories,
      isLoading,
      error: error as Error | null,
      getConditionMeta: (key: string) => conditionMap.get(key),
      getConditionsByCategory: () => {
        const grouped: Record<string, StrategyConditionInfo[]> = {};
        for (const c of conditions) {
          if (!grouped[c.category]) {
            grouped[c.category] = [];
          }
          grouped[c.category].push(c);
        }
        return grouped;
      },
      getDefaultParams: (key: string) => {
        const meta = conditionMap.get(key);
        if (!meta) return {};
        const params: Record<string, unknown> = {};
        for (const p of meta.params) {
          params[p.name] = p.default;
        }
        return params;
      },
    };
  }, [data, isLoading, error]);

  return (
    <ConditionsContext.Provider value={value}>
      {children}
    </ConditionsContext.Provider>
  );
}

export function useConditions(): ConditionsContextValue {
  const ctx = useContext(ConditionsContext);
  if (!ctx) {
    throw new Error('useConditions must be used within a ConditionsProvider');
  }
  return ctx;
}
