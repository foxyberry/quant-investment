'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ChevronDown, ChevronUp, Crown, Loader2, Medal } from 'lucide-react';
import Link from 'next/link';
import { getLeaderboard, type LeaderboardEntry } from '@/lib/api';

const SORT_OPTIONS = [
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'cagr', label: 'CAGR' },
  { value: 'total_return', label: 'Total Return' },
  { value: 'win_rate', label: 'Win Rate' },
  { value: 'max_drawdown', label: 'Max Drawdown' },
] as const;

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'draft', label: 'Draft' },
  { value: 'backtested', label: 'Backtested' },
  { value: 'validated', label: 'Validated' },
  { value: 'production', label: 'Production' },
] as const;

function formatPct(v: number | null): string {
  if (v === null || v === undefined) return '-';
  return `${(v * 100).toFixed(2)}%`;
}

function formatDec(v: number | null): string {
  if (v === null || v === undefined) return '-';
  return v.toFixed(3);
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) return <Crown className="h-4 w-4 text-yellow-500" />;
  if (rank === 2) return <Medal className="h-4 w-4 text-gray-400" />;
  if (rank === 3) return <Medal className="h-4 w-4 text-amber-600" />;
  return <span className="text-xs text-gray-400 w-4 text-center">{rank}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    backtested: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    validated: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    production: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    retired: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${colors[status] ?? colors.draft}`}>
      {status}
    </span>
  );
}

export default function LeaderboardPage() {
  const t = useTranslations('strategy');
  const [sortBy, setSortBy] = useState('sharpe_ratio');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['strategy', 'leaderboard', sortBy, order, statusFilter],
    queryFn: () =>
      getLeaderboard({
        sort_by: sortBy,
        order,
        status: statusFilter || undefined,
        limit: 50,
      }),
  });

  const toggleOrder = () => setOrder((o) => (o === 'desc' ? 'asc' : 'desc'));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#141415]">
      <div className="max-w-5xl mx-auto px-6 py-8">
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
              {t('leaderboardTitle')}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {t('leaderboardDescription')}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 font-medium">{t('sortBy')}</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1f] text-gray-900 dark:text-gray-100"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={toggleOrder}
            className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1f] text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            {order === 'desc' ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronUp className="h-3.5 w-3.5" />
            )}
            {order === 'desc' ? 'Desc' : 'Asc'}
          </button>

          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 font-medium">{t('statusFilter')}</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1f] text-gray-900 dark:text-gray-100"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 p-4 rounded-lg text-sm">
            {(error as Error).message}
          </div>
        )}

        {/* Table */}
        {data && (
          <>
            {data.entries.length === 0 ? (
              <div className="text-center py-20 text-gray-400">
                {t('noLeaderboardEntries')}
              </div>
            ) : (
              <div className="bg-white dark:bg-[#1e1e1f] rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                {/* Desktop table */}
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-[#1a1a1b]">
                        <th className="px-4 py-3 text-left text-gray-500 font-medium w-12">#</th>
                        <th className="px-4 py-3 text-left text-gray-500 font-medium">{t('strategyName')}</th>
                        <th className="px-4 py-3 text-left text-gray-500 font-medium">Status</th>
                        <th className="px-4 py-3 text-right text-gray-500 font-medium">Sharpe</th>
                        <th className="px-4 py-3 text-right text-gray-500 font-medium">CAGR</th>
                        <th className="px-4 py-3 text-right text-gray-500 font-medium">MDD</th>
                        <th className="px-4 py-3 text-right text-gray-500 font-medium">Win Rate</th>
                        <th className="px-4 py-3 text-right text-gray-500 font-medium">Return</th>
                        <th className="px-4 py-3 text-right text-gray-500 font-medium">Trades</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.entries.map((entry: LeaderboardEntry) => (
                        <tr
                          key={entry.strategy_id}
                          className="border-b border-gray-100 dark:border-gray-800 last:border-0 hover:bg-gray-50 dark:hover:bg-white/5"
                        >
                          <td className="px-4 py-3">
                            <RankBadge rank={entry.rank} />
                          </td>
                          <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                            {entry.strategy_name}
                          </td>
                          <td className="px-4 py-3">
                            <StatusBadge status={entry.status} />
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                            {formatDec(entry.sharpe_ratio)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                            {formatPct(entry.cagr)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-red-600 dark:text-red-400">
                            {formatPct(entry.max_drawdown)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                            {formatPct(entry.win_rate)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                            {formatPct(entry.total_return)}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">
                            {entry.total_trades}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Mobile cards */}
                <div className="md:hidden divide-y divide-gray-100 dark:divide-gray-800">
                  {data.entries.map((entry: LeaderboardEntry) => (
                    <div key={entry.strategy_id} className="px-4 py-4">
                      <div className="flex items-center gap-2 mb-2">
                        <RankBadge rank={entry.rank} />
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {entry.strategy_name}
                        </span>
                        <StatusBadge status={entry.status} />
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-gray-400">Sharpe</span>
                          <div className="font-mono text-gray-700 dark:text-gray-300">
                            {formatDec(entry.sharpe_ratio)}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-400">CAGR</span>
                          <div className="font-mono text-gray-700 dark:text-gray-300">
                            {formatPct(entry.cagr)}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-400">Win Rate</span>
                          <div className="font-mono text-gray-700 dark:text-gray-300">
                            {formatPct(entry.win_rate)}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <p className="text-xs text-gray-400 mt-3 text-right">
              {data.total_count} {t('strategiesRanked')}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
