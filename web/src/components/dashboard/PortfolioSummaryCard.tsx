'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui';
import { getPortfolioSummary } from '@/lib/api';
import type { PortfolioSummary } from '@/lib/types';
import { TrendingUp, TrendingDown, Briefcase, DollarSign } from 'lucide-react';

interface LoadingState {
  loading: boolean;
  error: string | null;
}

/**
 * Displays portfolio summary with total assets, P&L, and holdings count
 */
export default function PortfolioSummaryCard() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [state, setState] = useState<LoadingState>({ loading: true, error: null });

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await getPortfolioSummary();
        setSummary(data);
        setState({ loading: false, error: null });
      } catch (err) {
        setState({
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to load portfolio summary',
        });
      }
    };

    fetchSummary();
  }, []);

  const formatCurrency = (value: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  // Loading skeleton
  if (state.loading) {
    return (
      <Card title="Portfolio Overview">
        <div className="space-y-4 animate-pulse">
          <div className="h-8 w-32 rounded bg-[var(--border)]" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 rounded bg-[var(--border)]" />
            <div className="h-16 rounded bg-[var(--border)]" />
          </div>
        </div>
      </Card>
    );
  }

  // Error state
  if (state.error) {
    return (
      <Card title="Portfolio Overview">
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <Briefcase className="h-5 w-5" />
          <span>Unable to load portfolio data</span>
        </div>
        <p className="mt-2 text-sm text-red-500">{state.error}</p>
      </Card>
    );
  }

  // No data state
  if (!summary) {
    return (
      <Card title="Portfolio Overview">
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <Briefcase className="h-5 w-5" />
          <span>No portfolio data available</span>
        </div>
      </Card>
    );
  }

  const isProfitable = summary.total_pnl >= 0;
  const pnlColorClass = isProfitable ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  const PnlIcon = isProfitable ? TrendingUp : TrendingDown;

  return (
    <Card title="Portfolio Overview">
      <div className="space-y-4">
        {/* Total Market Value */}
        <div>
          <div className="flex items-center gap-2 text-sm text-[var(--foreground-muted)]">
            <DollarSign className="h-4 w-4" />
            <span>Total Market Value</span>
          </div>
          <p className="mt-1 text-3xl font-bold text-[var(--foreground)]">
            {formatCurrency(summary.total_market_value, summary.currency)}
          </p>
        </div>

        {/* P&L Section */}
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg bg-[var(--background)] p-3">
            <div className="flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
              <PnlIcon className={`h-4 w-4 ${pnlColorClass}`} />
              <span>Total P&L</span>
            </div>
            <p className={`mt-1 text-lg font-semibold ${pnlColorClass}`}>
              {formatCurrency(summary.total_pnl, summary.currency)}
            </p>
            <p className={`text-sm ${pnlColorClass}`}>
              {formatPercent(summary.total_pnl_pct)}
            </p>
          </div>

          <div className="rounded-lg bg-[var(--background)] p-3">
            <div className="flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
              <Briefcase className="h-4 w-4" />
              <span>Holdings</span>
            </div>
            <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">
              {summary.holdings_count}
            </p>
            <p className="text-sm text-[var(--foreground-muted)]">
              Active positions
            </p>
          </div>
        </div>

        {/* Investment Amount */}
        <div className="border-t border-[var(--border)] pt-3 text-sm text-[var(--foreground-muted)]">
          Total Investment: {formatCurrency(summary.total_investment, summary.currency)}
        </div>
      </div>
    </Card>
  );
}
