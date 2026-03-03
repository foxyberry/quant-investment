'use client';

import { memo, useState, useCallback, useRef, useEffect, Fragment } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  useNodesData,
  type EdgeProps,
} from '@xyflow/react';
import { Eye } from 'lucide-react';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import type { NodeIntermediateResult, StrategyResultItem } from '@/lib/api';
import { useTranslations, useLocale } from 'next-intl';

/** Known metric key → short display label */
const METRIC_LABELS: Record<string, string> = {
  pe_ratio: 'PER',
  pb_ratio: 'PBR',
  ps_ratio: 'PSR',
  pcf_ratio: 'PCF',
  roe_pct: 'ROE',
  roic_pct: 'ROIC',
  dividend_yield_pct: 'Div Yield',
  earnings_yield_pct: 'Earn Yield',
  ebit_ev_pct: 'EBIT/EV',
  fcf_yield_pct: 'FCF Yield',
  peg_ratio: 'PEG',
  debt_to_equity: 'D/E',
  current_ratio: 'Cur Ratio',
  f_score: 'F-Score',
  z_score: 'Z-Score',
  rsi: 'RSI',
  stoch_k: '%K',
  stoch_d: '%D',
  bb_width: 'BB Width',
  price_change_pct: 'Change',
  volume_ratio: 'Vol Ratio',
  obv_slope: 'OBV Slope',
};

function formatMetricKey(key: string): string {
  if (METRIC_LABELS[key]) return METRIC_LABELS[key];
  return key
    .replace(/_pct$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(key: string, value: unknown): string {
  if (typeof value !== 'number') return String(value);
  const isPct = key.endsWith('_pct');
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return isPct ? `${formatted}%` : formatted;
}

/** Extract primary metrics from condition details, filtering out bounds/errors. */
function extractPrimaryMetrics(
  details: Record<string, unknown>
): Array<{ label: string; value: string }> {
  return Object.entries(details)
    .filter(
      ([k, v]) =>
        typeof v === 'number' &&
        !k.startsWith('min_') &&
        !k.startsWith('max_') &&
        k !== 'error' &&
        k !== 'timestamp'
    )
    .slice(0, 2)
    .map(([k, v]) => ({
      label: formatMetricKey(k),
      value: formatMetricValue(k, v),
    }));
}

/** Get condition metric tags for a stock in context of a specific node. */
function getStockMetrics(
  stock: StrategyResultItem,
  nodeLabel: string,
  nodeType: string
): Array<{ label: string; value: string }> {
  if (!stock.conditions || stock.conditions.length === 0) return [];

  if (nodeType === 'condition') {
    const cond = stock.conditions.find((c) => {
      const name = c.condition_name as string;
      return name && name.startsWith(nodeLabel);
    });
    if (!cond || !cond.details) return [];
    return extractPrimaryMetrics(cond.details as Record<string, unknown>);
  }

  // For group/output: collect metrics from all matched conditions
  const metrics: Array<{ label: string; value: string }> = [];
  for (const cond of stock.conditions) {
    if (!cond.matched || !cond.details) continue;
    metrics.push(
      ...extractPrimaryMetrics(cond.details as Record<string, unknown>)
    );
    if (metrics.length >= 3) break;
  }
  return metrics.slice(0, 3);
}

/** Floating stock list popup that appears near the eye button. */
function StockListPopup({
  result,
  onClose,
}: {
  result: NodeIntermediateResult;
  onClose: () => void;
}) {
  const t = useTranslations('strategy');
  const tc = useTranslations('conditions');
  const locale = useLocale();
  const popupRef = useRef<HTMLDivElement>(null);

  // Translate condition labels via i18n, keep others as-is
  const displayLabel =
    result.node_type === 'condition' && tc.has(`${result.label}.label`)
      ? tc(`${result.label}.label`)
      : result.label;

  // Close on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div
      ref={popupRef}
      className="nodrag nowheel absolute top-full left-1/2 -translate-x-1/2 mt-2 w-80 z-50 rounded-xl border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] shadow-xl"
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-[#e1e3e5] dark:border-[#2e2e30] flex items-center justify-between">
        <div>
          <div className="text-[11px] font-semibold text-[#1313ec] dark:text-blue-400 uppercase tracking-wider">
            {displayLabel}
          </div>
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {result.stock_count.toLocaleString()}
            <span className="text-xs font-normal text-gray-500 ml-1">
              {t('stockCount')}
            </span>
          </div>
        </div>
      </div>

      {/* Stock list */}
      {result.stocks.length > 0 ? (
        <div className="max-h-60 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-white dark:bg-[#0b0b0c]">
              <tr className="text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-wider border-b border-[#e1e3e5] dark:border-[#2e2e30]">
                <th className="px-3 py-1.5 text-left">#</th>
                <th className="px-2 py-1.5 text-left">{t('ticker')}</th>
                <th className="px-2 py-1.5 text-left">{t('name')}</th>
                <th className="px-3 py-1.5 text-right">{t('price')}</th>
              </tr>
            </thead>
            <tbody>
              {result.stocks.slice(0, 30).map((stock, i) => {
                const metrics = getStockMetrics(
                  stock,
                  result.label,
                  result.node_type
                );
                return (
                  <Fragment key={stock.ticker}>
                    <tr
                      className="border-t border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-blue-50 dark:hover:bg-[#1313ec]/5 cursor-pointer transition-colors"
                      onClick={() => {
                        const width = 1000;
                        const height = 700;
                        const left = (screen.width - width) / 2;
                        const top = (screen.height - height) / 2;
                        window.open(
                          `/${locale}/analysis/${stock.ticker}?popup=true`,
                          `analysis_${stock.ticker}`,
                          `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
                        );
                      }}
                    >
                      <td className="px-3 py-1 text-gray-400">{i + 1}</td>
                      <td className="px-2 py-1 font-mono text-[#1313ec] font-medium text-[11px] underline decoration-[#1313ec]/30">
                        {stock.ticker}
                      </td>
                      <td className="px-2 py-1 text-gray-700 dark:text-gray-200 truncate max-w-[80px]">
                        {stock.name}
                      </td>
                      <td className="px-3 py-1 text-right text-gray-600 dark:text-gray-300">
                        {stock.current_price?.toLocaleString() ?? '-'}
                      </td>
                    </tr>
                    {metrics.length > 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 pb-1.5 pt-0">
                          <div className="flex flex-wrap gap-1">
                            {metrics.map((m) => (
                              <span
                                key={m.label}
                                className="text-[9px] px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-mono"
                              >
                                {m.label}: {m.value}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
          {result.stocks.length > 30 && (
            <div className="px-3 py-2 text-[10px] text-gray-400 text-center border-t border-[#e1e3e5] dark:border-[#2e2e30]">
              {t('andMore', { count: result.stocks.length - 30 })}
            </div>
          )}
        </div>
      ) : (
        <div className="px-3 py-4 text-xs text-gray-400 text-center">
          {result.node_type === 'universe' ? t('universeNote') : t('connectAndRun')}
        </div>
      )}
    </div>
  );
}

function LabeledEdge({
  id: _id,
  source,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps) {
  const t = useTranslations('strategy');
  const [showStockList, setShowStockList] = useState(false);
  const label = (data as Record<string, unknown>)?.label as string | undefined;
  const isOutputEdge = !label; // internal group edges have "Then" label

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 16,
    offset: isOutputEdge ? 36 : 28,
  });

  // Reactively subscribe to source node data so edge re-renders when results arrive
  const sourceNodeData = useNodesData(source);
  const sourceData = sourceNodeData?.data as unknown as StrategyNodeData | undefined;
  const intermediateResult = sourceData?.intermediateResult;
  const stockCount = intermediateResult?.stock_count;

  const handleToggleStockList = useCallback(() => {
    setShowStockList((prev) => !prev);
  }, []);

  const handleCloseStockList = useCallback(() => {
    setShowStockList(false);
  }, []);

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan absolute"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: stockCount !== undefined ? 'auto' : 'none',
          }}
        >
          {stockCount !== undefined ? (
            <div className="relative flex items-center gap-1">
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm ${
                  isOutputEdge
                    ? 'bg-[#1313ec] text-white border border-[#1313ec]'
                    : 'bg-white dark:bg-[#1e1e1f] text-[#1313ec] dark:text-blue-400 border border-[#e1e3e5] dark:border-[#2e2e30]'
                }`}
              >
                {stockCount.toLocaleString()} {t('stockCount')}
              </span>
              <button
                type="button"
                onClick={handleToggleStockList}
                className="w-5 h-5 flex items-center justify-center bg-white dark:bg-[#1e1e1f] border border-[#e1e3e5] dark:border-[#2e2e30] rounded-full shadow-sm hover:text-[#1313ec] transition-colors cursor-pointer"
              >
                <Eye className="h-3 w-3 text-gray-500 dark:text-gray-400" />
              </button>
              {showStockList && intermediateResult && (
                <StockListPopup
                  result={intermediateResult}
                  onClose={handleCloseStockList}
                />
              )}
            </div>
          ) : (
            <span className="bg-white dark:bg-[#1e1e1f] text-[10px] font-medium text-gray-400 dark:text-gray-500 px-2 py-0.5 rounded-full border border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm">
              {label ?? 'Then'}
            </span>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export default memo(LabeledEdge);
