'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, BarChart3, Loader2, Trophy } from 'lucide-react';
import Link from 'next/link';
import {
  listSavedStrategies,
  compareStrategies,
  type SavedStrategy,
} from '@/lib/api';

const METRIC_KEYS = [
  { key: 'sharpe_ratio', label: 'Sharpe Ratio', format: 'decimal', higherBetter: true },
  { key: 'sortino_ratio', label: 'Sortino Ratio', format: 'decimal', higherBetter: true },
  { key: 'cagr', label: 'CAGR', format: 'percent', higherBetter: true },
  { key: 'total_return', label: 'Total Return', format: 'percent', higherBetter: true },
  { key: 'max_drawdown', label: 'Max Drawdown', format: 'percent', higherBetter: false },
  { key: 'win_rate', label: 'Win Rate', format: 'percent', higherBetter: true },
  { key: 'profit_factor', label: 'Profit Factor', format: 'decimal', higherBetter: true },
  { key: 'total_trades', label: 'Total Trades', format: 'integer', higherBetter: true },
  { key: 'avg_trade_return', label: 'Avg Trade Return', format: 'percent', higherBetter: true },
] as const;

function formatValue(value: number | null, format: string): string {
  if (value === null || value === undefined) return '-';
  switch (format) {
    case 'percent':
      return `${(value * 100).toFixed(2)}%`;
    case 'decimal':
      return value.toFixed(3);
    case 'integer':
      return String(value);
    default:
      return String(value);
  }
}

export default function StrategyComparePage() {
  const t = useTranslations('strategy');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [showPicker, setShowPicker] = useState(false);

  const strategiesQuery = useQuery({
    queryKey: ['strategy', 'saved'],
    queryFn: listSavedStrategies,
  });

  const compareMutation = useMutation({
    mutationFn: (ids: string[]) => compareStrategies(ids),
  });

  const handleToggleStrategy = useCallback(
    (id: string) => {
      setSelectedIds((prev) => {
        if (prev.includes(id)) return prev.filter((x) => x !== id);
        if (prev.length >= 4) return prev;
        return [...prev, id];
      });
    },
    []
  );

  const handleCompare = useCallback(() => {
    if (selectedIds.length >= 2) {
      compareMutation.mutate(selectedIds);
      setShowPicker(false);
    }
  }, [selectedIds, compareMutation]);

  const result = compareMutation.data;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#141415]">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/strategy"
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {t('compareStrategies')}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {t('compareDescription')}
            </p>
          </div>
        </div>

        {/* Strategy picker */}
        {(!result || showPicker) && (
          <div className="bg-white dark:bg-[#1e1e1f] rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {t('selectStrategies')}
              </h2>
              <span className="text-sm text-gray-500">
                {selectedIds.length}/4 {t('selected')}
              </span>
            </div>

            {strategiesQuery.isLoading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            )}

            {strategiesQuery.data && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
                {strategiesQuery.data.strategies.map((s: SavedStrategy) => {
                  const isSelected = selectedIds.includes(s.id);
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => handleToggleStrategy(s.id)}
                      disabled={!isSelected && selectedIds.length >= 4}
                      className={`text-left p-3 rounded-lg border-2 transition-colors ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      } disabled:opacity-40 disabled:cursor-not-allowed`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {s.name}
                        </span>
                        {s.status && s.status !== 'draft' && (
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                            s.status === 'backtested' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                            s.status === 'validated' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                            'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                          }`}>
                            {s.status}
                          </span>
                        )}
                      </div>
                      {s.description && (
                        <p className="text-xs text-gray-400 mt-1 truncate">{s.description}</p>
                      )}
                    </button>
                  );
                })}
              </div>
            )}

            <button
              type="button"
              onClick={handleCompare}
              disabled={selectedIds.length < 2 || compareMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {compareMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <BarChart3 className="h-4 w-4" />
              )}
              {t('runComparison')}
            </button>
          </div>
        )}

        {/* Error */}
        {compareMutation.isError && (
          <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 p-4 rounded-lg mb-6 text-sm">
            {(compareMutation.error as Error).message}
          </div>
        )}

        {/* Results */}
        {result && !showPicker && (
          <>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                {result.strategies.map((s) => (
                  <span
                    key={s.strategy_id}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white dark:bg-[#1e1e1f] border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-900 dark:text-gray-100"
                  >
                    {s.strategy_name}
                  </span>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setShowPicker(true)}
                className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
              >
                {t('changeSelection')}
              </button>
            </div>

            {/* Metrics comparison table */}
            <div className="bg-white dark:bg-[#1e1e1f] rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden mb-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left px-4 py-3 text-gray-500 dark:text-gray-400 font-medium">
                      {t('metric')}
                    </th>
                    {result.strategies.map((s) => (
                      <th
                        key={s.strategy_id}
                        className="text-right px-4 py-3 text-gray-900 dark:text-gray-100 font-medium"
                      >
                        {s.strategy_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {METRIC_KEYS.map((metric) => {
                    const values = result.strategies.map((s) => ({
                      id: s.strategy_id,
                      val: s[metric.key as keyof typeof s] as number | null,
                    }));
                    const validValues = values.filter((v) => v.val !== null);
                    const bestId =
                      validValues.length > 0
                        ? validValues.sort((a, b) =>
                            metric.higherBetter
                              ? (b.val ?? 0) - (a.val ?? 0)
                              : (a.val ?? 0) - (b.val ?? 0)
                          )[0].id
                        : null;

                    return (
                      <tr
                        key={metric.key}
                        className="border-b border-gray-100 dark:border-gray-800 last:border-0"
                      >
                        <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">
                          {metric.label}
                        </td>
                        {result.strategies.map((s) => {
                          const val = s[metric.key as keyof typeof s] as number | null;
                          const isBest = s.strategy_id === bestId && val !== null;
                          return (
                            <td
                              key={s.strategy_id}
                              className={`text-right px-4 py-2.5 font-mono ${
                                isBest
                                  ? 'text-green-600 dark:text-green-400 font-semibold'
                                  : 'text-gray-900 dark:text-gray-100'
                              }`}
                            >
                              {isBest && <Trophy className="h-3 w-3 inline mr-1" />}
                              {formatValue(val, metric.format)}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
