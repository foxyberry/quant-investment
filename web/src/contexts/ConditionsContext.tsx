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

// Normalize category key to match i18n message keys (camelCase, lowercase first char).
// e.g. "Moving Average" -> "movingAverage", "Accumulation" -> "accumulation", "RSI" -> "rsi"
function normalizeCategoryKey(raw: string): string {
  // Already camelCase (e.g. "movingAverage") — return as-is if lowercase first char
  if (/^[a-z]/.test(raw) && !raw.includes(' ')) return raw;
  // Multi-word with spaces: "Moving Average" -> "movingAverage"
  if (raw.includes(' ')) {
    return raw
      .split(' ')
      .map((w, i) =>
        i === 0 ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()
      )
      .join('');
  }
  // Single capitalized word: "Accumulation" -> "accumulation", but keep "RSI" -> "rsi"
  if (raw === raw.toUpperCase()) return raw.toLowerCase();
  return raw.charAt(0).toLowerCase() + raw.slice(1);
}

export function ConditionsProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading, error } = useStrategyConditions();

  const value = useMemo<ConditionsContextValue>(() => {
    // Normalize category keys on conditions for i18n compatibility
    const rawConditions = data?.conditions ?? [];
    const conditions = rawConditions.map((c) => ({
      ...c,
      category: normalizeCategoryKey(c.category),
    }));
    const categories = (data?.categories ?? []).map(normalizeCategoryKey);

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
        for (const cat of Object.keys(grouped)) {
          grouped[cat].sort((a, b) => {
            if (a.recommended !== b.recommended) return a.recommended ? -1 : 1;
            if (a.order !== b.order) return a.order - b.order;
            return a.key.localeCompare(b.key);
          });
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
