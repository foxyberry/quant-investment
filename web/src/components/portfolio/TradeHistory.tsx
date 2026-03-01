'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { ArrowUpDown } from 'lucide-react';
import { getTradeHistory } from '@/lib/api';
import type { Trade } from '@/lib/types';
import { formatCurrency as formatCurrencyUtil } from '@/lib/format';

interface TradeHistoryProps {
  /** Additional CSS class names */
  className?: string;
}

type SortDirection = 'asc' | 'desc';

/**
 * Get color class based on P&L value
 */
function getPnlColorClass(value: number | null): string {
  if (value === null) return 'text-[var(--foreground-muted)]';
  if (value > 0) return 'text-green-600 dark:text-green-400';
  if (value < 0) return 'text-red-600 dark:text-red-400';
  return 'text-[var(--foreground-muted)]';
}

function getTradeTypeBadgeClass(tradeType: string): string {
  switch (tradeType) {
    case 'BUY':
      return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
    case 'ADJUST':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
    case 'SELL':
    default:
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
  }
}

/**
 * Inline section displaying trade history with a summary header,
 * a sortable table, and responsive mobile cards.
 */
export default function TradeHistory({ className }: TradeHistoryProps) {
  const t = useTranslations('portfolio');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency?: string) =>
    formatCurrencyUtil(value, currency, locale);

  const [trades, setTrades] = useState<Trade[]>([]);
  const [totalPnl, setTotalPnl] = useState(0);
  const [tradeCount, setTradeCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  useEffect(() => {
    let cancelled = false;

    const fetchTrades = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getTradeHistory();
        if (cancelled) return;
        setTrades(data.trades);
        setTotalPnl(data.total_realized_pnl);
        setTradeCount(data.trade_count);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : 'Failed to load trade history',
        );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    fetchTrades();
    return () => {
      cancelled = true;
    };
  }, []);

  const sortedTrades = useMemo(() => {
    return [...trades].sort((a, b) => {
      const comparison =
        new Date(a.traded_at).getTime() - new Date(b.traded_at).getTime();
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [trades, sortDirection]);

  const toggleSort = useCallback(() => {
    setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  }, []);

  const openAnalysis = useCallback(
    (ticker: string) => {
      const width = 1000;
      const height = 720;
      const left = (screen.width - width) / 2;
      const top = (screen.height - height) / 2;
      window.open(
        `/${locale}/analysis/${encodeURIComponent(ticker)}?popup=true`,
        `analysis_${ticker}`,
        `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`,
      );
    },
    [locale],
  );

  // Loading state
  if (isLoading) {
    return (
      <div
        className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] ${className ?? ''}`}
      >
        <div className="flex h-48 flex-col items-center justify-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--color-primary)]" />
          <p className="text-[var(--foreground-muted)]">{t('tradeLoading')}</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-6 ${className ?? ''}`}
      >
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
          <p className="font-medium">{t('errorLoading')}</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] overflow-hidden ${className ?? ''}`}
    >
      {/* Summary header */}
      <div className="border-b border-[var(--border)] px-6 py-4">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">
          {t('tradeHistoryTitle')}
        </h2>
        {tradeCount > 0 && (
          <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
            <div>
              <p className="text-xs text-[var(--foreground-muted)]">
                {t('tradeTotalPnl')}
              </p>
              <p
                className={`text-lg font-mono font-semibold ${getPnlColorClass(totalPnl)}`}
              >
                {totalPnl >= 0 ? '+' : ''}
                {formatCurrency(totalPnl, trades[0]?.currency)}
              </p>
            </div>
            <div>
              <p className="text-xs text-[var(--foreground-muted)]">
                {t('tradeCount', { count: tradeCount.toString() })}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Empty state */}
      {trades.length === 0 && (
        <div className="flex h-48 flex-col items-center justify-center gap-4">
          <p className="text-[var(--foreground-muted)]">
            {t('tradeHistoryEmpty')}
          </p>
        </div>
      )}

      {/* Table content */}
      {trades.length > 0 && (
        <>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--background)]/50">
                  <th className="px-4 py-3 text-left">
                    <button
                      type="button"
                      onClick={toggleSort}
                      className="flex items-center gap-1 font-semibold text-[var(--foreground)] hover:text-[var(--color-primary)] transition-colors"
                    >
                      {t('tradeDate')}
                      <ArrowUpDown
                        className={`h-4 w-4 text-[var(--color-primary)] ${
                          sortDirection === 'desc' ? 'rotate-180' : ''
                        }`}
                      />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-[var(--foreground)]">
                    {t('tradeTicker')}
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-[var(--foreground)]">
                    {t('tradeName')}
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-[var(--foreground)]">
                    {t('tradeType')}
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                    {t('tradeQty')}
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                    {t('tradePrice')}
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                    {t('tradeFee')}
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                    {t('tradeTax')}
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                    {t('tradeAvgPrice')}
                  </th>
                  <th className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                    {t('tradeRealizedPnl')}
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-[var(--foreground)]">
                    {t('tradeNote')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedTrades.map((trade) => (
                  <tr
                    key={trade.id}
                    className="border-b border-[var(--border)] hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-[var(--foreground)]">
                      {trade.traded_at}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => openAnalysis(trade.ticker)}
                        className="font-mono font-medium text-[var(--color-primary)] hover:underline cursor-pointer"
                      >
                        {trade.ticker}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground)]">
                      {trade.name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${getTradeTypeBadgeClass(trade.trade_type)}`}>
                        {trade.trade_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                      {trade.quantity.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                      {formatCurrency(trade.price, trade.currency)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--foreground-muted)]">
                      {formatCurrency(trade.fee, trade.currency)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--foreground-muted)]">
                      {formatCurrency(trade.tax ?? 0, trade.currency)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                      {trade.avg_price_at_trade !== null
                        ? formatCurrency(
                            trade.avg_price_at_trade,
                            trade.currency,
                          )
                        : '-'}
                    </td>
                    <td
                      className={`px-4 py-3 text-right font-mono ${getPnlColorClass(
                        trade.realized_pnl,
                      )}`}
                    >
                      {trade.realized_pnl !== null
                        ? `${trade.realized_pnl >= 0 ? '+' : ''}${formatCurrency(
                            trade.realized_pnl,
                            trade.currency,
                          )}`
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-[var(--foreground-muted)] max-w-[200px] truncate">
                      {trade.note || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="md:hidden divide-y divide-[var(--border)]">
            {sortedTrades.map((trade) => (
              <div key={trade.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openAnalysis(trade.ticker)}
                      className="font-mono font-medium text-[var(--color-primary)] hover:underline cursor-pointer"
                    >
                      {trade.ticker}
                    </button>
                    {trade.name && (
                      <span className="text-sm text-[var(--foreground)]">
                        {trade.name}
                      </span>
                    )}
                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${getTradeTypeBadgeClass(trade.trade_type)}`}>
                      {trade.trade_type}
                    </span>
                  </div>
                  <span className="text-sm text-[var(--foreground-muted)] font-mono">
                    {trade.traded_at}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-[var(--foreground-muted)]">
                      {t('tradeQty')}
                    </p>
                    <p className="font-mono text-[var(--foreground)]">
                      {trade.quantity.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-[var(--foreground-muted)]">
                      {t('tradePrice')}
                    </p>
                    <p className="font-mono text-[var(--foreground)]">
                      {formatCurrency(trade.price, trade.currency)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[var(--foreground-muted)]">
                      {t('tradeRealizedPnl')}
                    </p>
                    <p
                      className={`font-mono ${getPnlColorClass(trade.realized_pnl)}`}
                    >
                      {trade.realized_pnl !== null
                        ? `${trade.realized_pnl >= 0 ? '+' : ''}${formatCurrency(
                            trade.realized_pnl,
                            trade.currency,
                          )}`
                        : '-'}
                    </p>
                  </div>
                  <div>
                    <p className="text-[var(--foreground-muted)]">
                      {t('tradeFee')}
                    </p>
                    <p className="font-mono text-[var(--foreground-muted)]">
                      {formatCurrency(trade.fee, trade.currency)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[var(--foreground-muted)]">
                      {t('tradeTax')}
                    </p>
                    <p className="font-mono text-[var(--foreground-muted)]">
                      {formatCurrency(trade.tax ?? 0, trade.currency)}
                    </p>
                  </div>
                </div>
                {trade.note && (
                  <p className="text-sm text-[var(--foreground-muted)]">
                    {trade.note}
                  </p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
