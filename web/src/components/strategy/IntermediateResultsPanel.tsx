'use client';

import { useState, useCallback, useMemo } from 'react';
import { ChevronDown, ChevronUp, Flag, Maximize2, Minimize2 } from 'lucide-react';
import { useTranslations, useLocale } from 'next-intl';
import type { NodeIntermediateResult, StrategyResultItem } from '@/lib/api';

/** Extract metric values (numeric + date strings) from a stock's condition details. */
function extractMetrics(
  stock: StrategyResultItem
): Record<string, number | string> {
  const metrics: Record<string, number | string> = {};
  if (!stock.conditions) return metrics;
  for (const cond of stock.conditions) {
    const details = cond.details as Record<string, unknown> | undefined;
    if (!details) continue;
    for (const [k, v] of Object.entries(details)) {
      if (k === 'cross_day') continue; // hidden: redundant with cross_date
      if (
        typeof v === 'string' &&
        k.endsWith('_date')
      ) {
        metrics[k] = v;
      } else if (
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
  cross_date: 'Cross Date',
};

function formatMetric(key: string, value: number | string): string {
  if (typeof value === 'string') return value;
  const isPct = key.endsWith('_pct');
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return isPct ? `${formatted}%` : formatted;
}

function metricLabel(key: string): string {
  return METRIC_LABELS[key] || key.replace(/_pct$/, '').replace(/_/g, ' ');
}

/** Determine common metric columns across all stocks in a result. */
function detectMetricColumns(
  stocks: StrategyResultItem[],
  preferredMetricKey?: string
): string[] {
  const freq: Record<string, number> = {};
  const sample = stocks.slice(0, 50);
  for (const stock of sample) {
    const m = extractMetrics(stock);
    for (const k of Object.keys(m)) {
      freq[k] = (freq[k] || 0) + 1;
    }
  }
  const sortedAll = Object.entries(freq).sort((a, b) => b[1] - a[1]);
  if (sortedAll.length === 0) return [];

  // Use sample-based threshold (not full stock_count) to avoid empty columns on large tabs.
  const threshold = Math.max(1, Math.ceil(sample.length * 0.3));
  const selected = sortedAll
    .filter(([, count]) => count >= threshold)
    .slice(0, 4)
    .map(([k]) => k);

  // Fallback: if threshold removed everything, still show top-used metrics.
  const columns = selected.length > 0 ? selected : sortedAll.slice(0, 4).map(([k]) => k);

  if (!preferredMetricKey) return columns;
  const normalized = preferredMetricKey.toLowerCase();
  const preferred = columns.find((k) => {
    const lower = k.toLowerCase();
    return (
      lower === normalized ||
      lower.includes(normalized) ||
      normalized.includes(lower)
    );
  });
  if (!preferred) return columns;

  return [preferred, ...columns.filter((k) => k !== preferred)];
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

/** Compute topological order from edges for pipeline-flow tab sorting. */
function topoOrder(
  edges: Array<{ source: string; target: string }>
): Map<string, number> {
  const graph = new Map<string, string[]>();
  const inDegree = new Map<string, number>();

  for (const e of edges) {
    if (!graph.has(e.source)) graph.set(e.source, []);
    graph.get(e.source)!.push(e.target);
    inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
    if (!inDegree.has(e.source)) inDegree.set(e.source, 0);
  }

  const queue = [...inDegree.entries()]
    .filter(([, d]) => d === 0)
    .map(([n]) => n);
  const order = new Map<string, number>();
  let idx = 0;
  while (queue.length > 0) {
    const node = queue.shift()!;
    order.set(node, idx++);
    for (const next of graph.get(node) || []) {
      const d = inDegree.get(next)! - 1;
      inDegree.set(next, d);
      if (d === 0) queue.push(next);
    }
  }
  return order;
}

interface IntermediateResultsPanelProps {
  nodeResults: Record<string, NodeIntermediateResult> | null;
  finalResults: StrategyResultItem[] | null;
  selectedNodeId: string | null;
  isPending: boolean;
  deployProgress: number;
  conditionCount: number;
  progressDetail?: { processed: number; total: number; matched: number } | null;
  edges?: Array<{ source: string; target: string }>;
}

export default function IntermediateResultsPanel({
  nodeResults,
  finalResults,
  selectedNodeId,
  isPending,
  deployProgress,
  conditionCount,
  progressDetail,
  edges,
}: IntermediateResultsPanelProps) {
  const t = useTranslations('strategy');
  const tConditions = useTranslations('conditions');
  const locale = useLocale();
  const [collapsed, setCollapsed] = useState(false);
  const [expanded, setExpanded] = useState(false);
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
      // Secondary sort: topological (pipeline) position within the same type
      const pipelineOrder = edges ? topoOrder(edges) : new Map<string, number>();
      const sorted = Object.values(nodeResults)
        .filter((nr) => nr.node_type !== 'output') // output is shown as __output__ tab
        .sort((a, b) => {
          const typeDiff =
            (typeOrder[a.node_type] ?? 9) - (typeOrder[b.node_type] ?? 9);
          if (typeDiff !== 0) return typeDiff;
          // Same type: sort by pipeline position
          return (
            (pipelineOrder.get(a.node_id) ?? 999) -
            (pipelineOrder.get(b.node_id) ?? 999)
          );
        });
      for (const nr of sorted) {
        let label: string;
        if (nr.node_type === 'condition') {
          // Use i18n key: conditions.{condition_type}.label
          const i18nKey = `${nr.label}.label`;
          label = tConditions.has(i18nKey)
            ? tConditions(i18nKey)
            : formatTabLabel(nr.label, nr.node_type);
        } else {
          label = formatTabLabel(nr.label, nr.node_type);
        }
        result.push({
          id: nr.node_id,
          label,
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
  }, [nodeResults, finalResults, t, tConditions, edges]);

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

  const preferredMetricKey = useMemo(() => {
    if (!nodeResults || effectiveTab === '__output__') return undefined;
    const currentNode = nodeResults[effectiveTab];
    if (!currentNode || currentNode.node_type !== 'condition') return undefined;
    return currentNode.label;
  }, [nodeResults, effectiveTab]);

  const metricColumns = useMemo(
    () => detectMetricColumns(currentStocks, preferredMetricKey),
    [currentStocks, preferredMetricKey]
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
          {tabs.map((tab, index) => {
            const isActive = effectiveTab === tab.id;
            const isOutput = tab.id === '__output__';
            const stepNumber = String.fromCodePoint(0x2460 + index); // ①②③...
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
                <span className="opacity-60">{stepNumber}</span>
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
        <div className="flex items-center">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="px-2 py-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title={expanded ? t('collapsePanel') : t('expandPanel')}
          >
            {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="px-2 py-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            {collapsed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Content */}
      {!collapsed && (
        <div className={`${expanded ? 'max-h-[70vh]' : 'max-h-64'} overflow-y-auto transition-[max-height] duration-300`}>
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
                  <th className="px-3 py-2">{t('market')}</th>
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
                      <td className="px-3 py-1.5">
                        {stock.market && (
                          <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                            stock.market === 'KOSDAQ'
                              ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
                              : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                          }`}>
                            {stock.market}
                          </span>
                        )}
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
