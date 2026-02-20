'use client';

import { useState, useCallback, useMemo } from 'react';
import { ChevronDown, ChevronUp, Flag } from 'lucide-react';
import { useTranslations, useLocale } from 'next-intl';
import type { NodeIntermediateResult, StrategyResultItem } from '@/lib/api';

/** Extract numeric metric values from a stock's condition details. */
function extractMetrics(
  stock: StrategyResultItem
): Record<string, number> {
  const metrics: Record<string, number> = {};
  if (!stock.conditions) return metrics;
  for (const cond of stock.conditions) {
    const details = cond.details as Record<string, unknown> | undefined;
    if (!details) continue;
    for (const [k, v] of Object.entries(details)) {
      if (
        typeof v === 'number' &&
        !k.startsWith('min_') &&
        !k.startsWith('max_') &&
        k !== 'error' &&
        k !== 'timestamp'
      ) {
        metrics[k] = v;
      }
    }
  }
  return metrics;
}

const METRIC_LABELS: Record<string, string> = {
  pe_ratio: 'PER',
  pb_ratio: 'PBR',
  ps_ratio: 'PSR',
  dividend_yield_pct: 'Div%',
  roe_pct: 'ROE%',
  rsi: 'RSI',
  current_ratio: 'CR',
  debt_to_equity: 'D/E',
  f_score: 'F',
  earnings_yield_pct: 'EY%',
};

function formatMetric(key: string, value: number): string {
  const isPct = key.endsWith('_pct');
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return isPct ? `${formatted}%` : formatted;
}

function metricLabel(key: string): string {
  return METRIC_LABELS[key] || key.replace(/_pct$/, '').replace(/_/g, ' ');
}

/** Determine common metric columns across all stocks in a result. */
function detectMetricColumns(stocks: StrategyResultItem[]): string[] {
  const freq: Record<string, number> = {};
  for (const stock of stocks.slice(0, 50)) {
    const m = extractMetrics(stock);
    for (const k of Object.keys(m)) {
      freq[k] = (freq[k] || 0) + 1;
    }
  }
  // Show metrics present in >30% of stocks, up to 4 columns
  const threshold = Math.max(1, stocks.length * 0.3);
  return Object.entries(freq)
    .filter(([, count]) => count >= threshold)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([k]) => k);
}

interface Tab {
  id: string;
  label: string;
  count: number;
  nodeType: string;
}

/** Convert raw backend label (e.g. "pcf_ratio") to readable tab name. */
function formatTabLabel(label: string, nodeType: string): string {
  if (nodeType === 'universe' || nodeType === 'sector') return label;
  // Condition labels: snake_case → Title Case
  if (METRIC_LABELS[label]) return METRIC_LABELS[label];
  return label
    .replace(/_pct$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface IntermediateResultsPanelProps {
  nodeResults: Record<string, NodeIntermediateResult> | null;
  finalResults: StrategyResultItem[] | null;
  selectedNodeId: string | null;
  isPending: boolean;
  deployProgress: number;
  conditionCount: number;
  progressDetail?: { processed: number; total: number; matched: number } | null;
}

export default function IntermediateResultsPanel({
  nodeResults,
  finalResults,
  selectedNodeId,
  isPending,
  deployProgress,
  conditionCount,
  progressDetail,
}: IntermediateResultsPanelProps) {
  const t = useTranslations('strategy');
  const locale = useLocale();
  const [collapsed, setCollapsed] = useState(false);
  const [activeTabId, setActiveTabId] = useState<string>('__output__');

  // Build tabs from node results + output
  const tabs: Tab[] = useMemo(() => {
    const result: Tab[] = [];
    if (nodeResults) {
      // Sort by node_type order: universe → sector → condition → logic
      const typeOrder: Record<string, number> = {
        universe: 0,
        sector: 1,
        condition: 2,
        logic: 3,
      };
      const sorted = Object.values(nodeResults)
        .filter((nr) => nr.node_type !== 'output') // output is shown as __output__ tab
        .sort(
          (a, b) => (typeOrder[a.node_type] ?? 9) - (typeOrder[b.node_type] ?? 9)
        );
      for (const nr of sorted) {
        result.push({
          id: nr.node_id,
          label: formatTabLabel(nr.label, nr.node_type),
          count: nr.stock_count,
          nodeType: nr.node_type,
        });
      }
    }
    if (finalResults) {
      result.push({
        id: '__output__',
        label: t('finalOutput'),
        count: finalResults.length,
        nodeType: 'output',
      });
    }
    return result;
  }, [nodeResults, finalResults, t]);

  // Sync active tab when canvas node is clicked
  const effectiveTab = useMemo(() => {
    if (selectedNodeId && tabs.some((t) => t.id === selectedNodeId)) {
      return selectedNodeId;
    }
    return activeTabId;
  }, [selectedNodeId, activeTabId, tabs]);

  const handleTabClick = useCallback((tabId: string) => {
    setActiveTabId(tabId);
  }, []);

  // Current data for the active tab
  const currentStocks: StrategyResultItem[] = useMemo(() => {
    if (effectiveTab === '__output__') return finalResults || [];
    if (nodeResults && nodeResults[effectiveTab]) {
      return nodeResults[effectiveTab].stocks;
    }
    return [];
  }, [effectiveTab, nodeResults, finalResults]);

  const metricColumns = useMemo(
    () => detectMetricColumns(currentStocks),
    [currentStocks]
  );

  const hasContent = isPending || tabs.length > 0;
  if (!hasContent) return null;

  const openPopup = (ticker: string) => {
    const width = 1000;
    const height = 700;
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;
    window.open(
      `/${locale}/analysis/${ticker}?popup=true`,
      `analysis_${ticker}`,
      `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
    );
  };

  return (
    <div className="border-t border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c]">
      {/* Tab bar */}
      <div className="flex items-center border-b border-[#e1e3e5] dark:border-[#2e2e30]">
        <div className="flex-1 flex items-center gap-0 overflow-x-auto px-2">
          {tabs.map((tab) => {
            const isActive = effectiveTab === tab.id;
            const isOutput = tab.id === '__output__';
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleTabClick(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                  isActive
                    ? 'border-[#1313ec] text-[#1313ec] dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                {isOutput && <Flag className="h-3 w-3" />}
                <span>{tab.label}</span>
                <span
                  className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                    isActive
                      ? 'bg-[#1313ec]/10 text-[#1313ec] dark:text-blue-400'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {tab.count.toLocaleString()}
                </span>
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="px-3 py-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          {collapsed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Content */}
      {!collapsed && (
        <div className="max-h-64 overflow-y-auto">
          {isPending ? (
            <div className="flex flex-col items-center justify-center py-10 text-gray-400 dark:text-gray-500">
              <div className="w-64 mb-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-medium">{t('deployProgress')}</span>
                  <span className="font-bold text-[#1313ec]">
                    {Math.min(Math.round(deployProgress), 100)}%
                  </span>
                </div>
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#1313ec] rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${Math.min(deployProgress, 100)}%` }}
                  />
                </div>
              </div>
              <span className="text-sm">{t('runningStrategy')}</span>
              <span className="text-xs mt-1">
                {progressDetail && progressDetail.total > 0
                  ? t('progressTickers', {
                      processed: progressDetail.processed,
                      total: progressDetail.total,
                      matched: progressDetail.matched,
                    })
                  : t('processingConditions', { count: conditionCount })}
              </span>
            </div>
          ) : currentStocks.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider border-b border-[#e1e3e5] dark:border-[#2e2e30] sticky top-0 bg-white dark:bg-[#0b0b0c]">
                  <th className="px-4 py-2 w-10">#</th>
                  <th className="px-4 py-2">{t('ticker')}</th>
                  <th className="px-4 py-2">{t('name')}</th>
                  <th className="px-4 py-2 text-right">{t('price')}</th>
                  {metricColumns.map((col) => (
                    <th key={col} className="px-3 py-2 text-right">
                      {metricLabel(col)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {currentStocks.map((stock, i) => {
                  const metrics = extractMetrics(stock);
                  return (
                    <tr
                      key={stock.ticker}
                      className="border-b border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-colors cursor-pointer"
                      onClick={() => openPopup(stock.ticker)}
                    >
                      <td className="px-4 py-1.5 text-gray-400 text-xs">
                        {i + 1}
                      </td>
                      <td className="px-4 py-1.5 font-mono text-[#1313ec] font-medium text-[11px] underline decoration-[#1313ec]/30">
                        {stock.ticker}
                      </td>
                      <td className="px-4 py-1.5 text-gray-700 dark:text-gray-200 truncate max-w-[120px]">
                        {stock.name}
                      </td>
                      <td className="px-4 py-1.5 text-right text-gray-700 dark:text-gray-200">
                        {stock.current_price?.toLocaleString() ?? '-'}
                      </td>
                      {metricColumns.map((col) => (
                        <td
                          key={col}
                          className="px-3 py-1.5 text-right text-xs text-gray-600 dark:text-gray-300 font-mono"
                        >
                          {metrics[col] !== undefined
                            ? formatMetric(col, metrics[col])
                            : '-'}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="px-4 py-8 text-center text-xs text-gray-400">
              {t('noResultsForNode')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
