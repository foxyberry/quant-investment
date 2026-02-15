'use client';

import type { BacktestTrade } from '@/lib/api';
import { useTranslations } from 'next-intl';

interface TradesTableProps {
  trades: BacktestTrade[];
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-';
  // Accept ISO date strings; display as YYYY-MM-DD
  return dateStr.slice(0, 10);
}

function formatPrice(price: number): string {
  return price.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function formatPnl(pnl: number): string {
  const sign = pnl >= 0 ? '+' : '';
  return `${sign}${pnl.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

function formatReturn(pct: number): string {
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${(pct * 100).toFixed(2)}%`;
}

export default function TradesTable({ trades }: TradesTableProps) {
  const t = useTranslations('backtest');
  const totalPnl = trades.reduce((sum, tr) => sum + tr.pnl, 0);
  const avgReturn =
    trades.length > 0
      ? trades.reduce((sum, tr) => sum + tr.return_pct, 0) / trades.length
      : 0;

  return (
    <div className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] overflow-hidden">
      <div className="max-h-60 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-gray-50 dark:bg-[#1e1e1f] z-10">
            <tr className="text-left text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider border-b border-[#e1e3e5] dark:border-[#2e2e30]">
              <th className="px-3 py-2">{t('entry')}</th>
              <th className="px-3 py-2">{t('exit')}</th>
              <th className="px-3 py-2 text-right">{t('entryPrice')}</th>
              <th className="px-3 py-2 text-right">{t('exitPrice')}</th>
              <th className="px-3 py-2 text-right">{t('pnl')}</th>
              <th className="px-3 py-2 text-right">{t('return')}</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, idx) => (
              <tr
                key={idx}
                className="border-b border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
              >
                <td className="px-3 py-1.5 text-gray-600 dark:text-gray-300 font-mono">
                  {formatDate(trade.entry_date)}
                </td>
                <td className="px-3 py-1.5 text-gray-600 dark:text-gray-300 font-mono">
                  {formatDate(trade.exit_date)}
                </td>
                <td className="px-3 py-1.5 text-right text-gray-700 dark:text-gray-200">
                  {formatPrice(trade.entry_price)}
                </td>
                <td className="px-3 py-1.5 text-right text-gray-700 dark:text-gray-200">
                  {formatPrice(trade.exit_price)}
                </td>
                <td
                  className={`px-3 py-1.5 text-right font-medium ${
                    trade.pnl >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatPnl(trade.pnl)}
                </td>
                <td
                  className={`px-3 py-1.5 text-right font-medium ${
                    trade.return_pct >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatReturn(trade.return_pct)}
                </td>
              </tr>
            ))}
          </tbody>
          {trades.length > 0 && (
            <tfoot className="border-t-2 border-[#e1e3e5] dark:border-[#2e2e30] bg-gray-50 dark:bg-[#1e1e1f]">
              <tr>
                <td
                  colSpan={4}
                  className="px-3 py-2 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider"
                >
                  {t('totalTrades', { count: trades.length })}
                </td>
                <td
                  className={`px-3 py-2 text-right font-bold ${
                    totalPnl >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatPnl(totalPnl)}
                </td>
                <td
                  className={`px-3 py-2 text-right font-bold ${
                    avgReturn >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatReturn(avgReturn)}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
