'use client';

import { useMemo } from 'react';
import { X, ExternalLink, Eye } from 'lucide-react';
import { useTranslations, useLocale } from 'next-intl';
import type { NodeIntermediateResult, StrategyResultItem } from '@/lib/api';

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

function extractTopMetric(stock: StrategyResultItem): { key: string; value: number } | null {
  if (!stock.conditions) return null;
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
        return { key: k, value: v };
      }
    }
  }
  return null;
}

function metricLabel(key: string): string {
  return METRIC_LABELS[key] || key.replace(/_pct$/, '').replace(/_/g, ' ');
}

interface SideInspectionPanelProps {
  nodeResult: NodeIntermediateResult | null;
  totalStocks: number | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function SideInspectionPanel({
  nodeResult,
  totalStocks,
  isOpen,
  onClose,
}: SideInspectionPanelProps) {
  const t = useTranslations('strategy');
  const tCond = useTranslations('conditions');
  const locale = useLocale();

  const nodeLabel = useMemo(() => {
    if (!nodeResult) return '';
    if (nodeResult.node_type === 'condition') {
      const i18nKey = `${nodeResult.label}.label`;
      if (tCond.has(i18nKey)) return tCond(i18nKey);
    }
    return nodeResult.label
      .replace(/_pct$/, '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }, [nodeResult, tCond]);

  const passRate = useMemo(() => {
    if (!nodeResult || !totalStocks || totalStocks === 0) return null;
    return ((nodeResult.stock_count / totalStocks) * 100).toFixed(1);
  }, [nodeResult, totalStocks]);

  const topStocks = useMemo(
    () => (nodeResult?.stocks || []).slice(0, 10),
    [nodeResult]
  );

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
    <div
      className={`fixed top-0 right-0 h-full w-[380px] z-40 bg-white dark:bg-[#0b0b0c] border-l border-[#e1e3e5] dark:border-[#2e2e30] shadow-2xl transition-transform duration-300 ease-out ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
        <div className="flex items-center gap-2">
          <Eye className="h-4 w-4 text-[#1313ec]" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {nodeResult
              ? t('inspectionOf', { label: nodeLabel })
              : t('inspectNode')}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <X className="h-4 w-4 text-gray-400" />
        </button>
      </div>

      {nodeResult ? (
        <div className="flex flex-col h-[calc(100%-53px)]">
          {/* Stats */}
          <div className="px-4 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {t('stocksPassingFilter', {
                  passed: nodeResult.stock_count.toLocaleString(),
                  total: totalStocks?.toLocaleString() ?? '—',
                })}
              </span>
              {passRate && (
                <span className="text-lg font-bold text-[#1313ec] dark:text-blue-400">
                  {t('passRate', { rate: passRate })}
                </span>
              )}
            </div>
            {/* Pass rate bar */}
            {passRate && (
              <div className="mt-2 w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#1313ec] rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(parseFloat(passRate), 100)}%` }}
                />
              </div>
            )}
          </div>

          {/* Top Results Preview */}
          <div className="flex-1 overflow-y-auto">
            <div className="px-4 py-2">
              <h4 className="text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                {t('topResultsPreview')}
              </h4>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider border-b border-[#e1e3e5] dark:border-[#2e2e30] sticky top-0 bg-white dark:bg-[#0b0b0c]">
                  <th className="px-4 py-1.5">Symbol</th>
                  <th className="px-3 py-1.5 text-right">Value</th>
                  <th className="px-3 py-1.5 text-right">{t('price')}</th>
                </tr>
              </thead>
              <tbody>
                {topStocks.map((stock) => {
                  const metric = extractTopMetric(stock);
                  return (
                    <tr
                      key={stock.ticker}
                      className="border-b border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-colors cursor-pointer"
                      onClick={() => openPopup(stock.ticker)}
                    >
                      <td className="px-4 py-1.5">
                        <span className="font-mono text-[11px] font-medium text-[#1313ec] dark:text-blue-400">
                          {stock.ticker}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-right text-xs text-gray-600 dark:text-gray-300 font-mono">
                        {metric ? (
                          <span title={metricLabel(metric.key)}>
                            {metric.value.toFixed(2)}
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="px-3 py-1.5 text-right text-xs text-gray-700 dark:text-gray-200">
                        {stock.current_price?.toLocaleString() ?? '-'}
                      </td>
                    </tr>
                  );
                })}
                {topStocks.length === 0 && (
                  <tr>
                    <td
                      colSpan={3}
                      className="px-4 py-6 text-center text-xs text-gray-400"
                    >
                      {t('noResultsForNode')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            {nodeResult.stocks.length > 10 && (
              <div className="px-4 py-2 text-xs text-gray-400 dark:text-gray-500">
                {t('andMore', { count: nodeResult.stocks.length - 10 })}
              </div>
            )}
          </div>

          {/* Footer CTA */}
          <div className="px-4 py-3 border-t border-[#e1e3e5] dark:border-[#2e2e30]">
            <button
              type="button"
              className="flex items-center justify-center gap-2 w-full px-4 py-2 text-sm font-medium text-[#1313ec] dark:text-blue-400 border border-[#1313ec]/30 dark:border-blue-400/30 rounded-lg hover:bg-[#1313ec]/5 dark:hover:bg-blue-400/5 transition-colors"
              onClick={onClose}
            >
              <ExternalLink className="h-3.5 w-3.5" />
              {t('openFullDataset')}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-[calc(100%-53px)]">
          <p className="text-sm text-gray-400 dark:text-gray-500">
            {t('inspectNode')}
          </p>
        </div>
      )}
    </div>
  );
}
