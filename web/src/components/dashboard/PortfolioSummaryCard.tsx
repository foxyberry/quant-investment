'use client';

import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Card } from '@/components/ui';
import { getPortfolioSummary } from '@/lib/api';
import type { PortfolioSummary } from '@/lib/types';
import { TrendingUp, TrendingDown, Briefcase, DollarSign, ArrowRight } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { formatCurrency as formatCurrencyUtil, formatPercent as formatPercentUtil } from '@/lib/format';
import { useUserSettings } from '@/contexts/UserSettingsContext';

interface LoadingState {
  loading: boolean;
  error: string | null;
}

export default function PortfolioSummaryCard() {
  const t = useTranslations('dashboard');
  const locale = useLocale();
  const { settings } = useUserSettings();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [state, setState] = useState<LoadingState>({ loading: true, error: null });

  useEffect(() => {
    const fetchSummary = async () => {
      setState((prev) => ({ ...prev, loading: true }));
      try {
        const data = await getPortfolioSummary(settings.baseCurrency);
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
  }, [settings.baseCurrency]);

  const formatCurrency = (value: number, currency: string = 'USD') =>
    formatCurrencyUtil(value, currency, locale);

  const formatPercent = (value: number) => formatPercentUtil(value);

  if (state.loading) {
    return (
      <Card title={t('portfolioOverview')}>
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

  if (state.error) {
    return (
      <Card title={t('portfolioOverview')}>
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <Briefcase className="h-5 w-5" />
          <span>{t('unableToLoadPortfolio')}</span>
        </div>
        <p className="mt-2 text-sm text-red-500">{state.error}</p>
      </Card>
    );
  }

  if (!summary) {
    return (
      <Card title={t('portfolioOverview')}>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <Briefcase className="mb-3 h-10 w-10 text-[var(--foreground-muted)]" />
          <p className="text-[var(--foreground-muted)]">{t('noPortfolioData')}</p>
          <Link
            href="/portfolio"
            className="mt-3 inline-flex items-center gap-1 rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            {t('goToPortfolio')}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </Card>
    );
  }

  const isProfitable = summary.total_pnl >= 0;
  const pnlColorClass = isProfitable ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  const PnlIcon = isProfitable ? TrendingUp : TrendingDown;

  return (
    <Card title={t('portfolioOverview')}>
      <div className="space-y-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-[var(--foreground-muted)]">
            <DollarSign className="h-4 w-4" />
            <span>{t('totalMarketValue')}</span>
          </div>
          <p className="mt-1 text-3xl font-bold text-[var(--foreground)]">
            {formatCurrency(summary.total_market_value, summary.currency)}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg bg-[var(--background)] p-3">
            <div className="flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
              <PnlIcon className={`h-4 w-4 ${pnlColorClass}`} />
              <span>{t('totalPnl')}</span>
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
              <span>{t('holdings')}</span>
            </div>
            <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">
              {summary.holdings_count}
            </p>
            <p className="text-sm text-[var(--foreground-muted)]">
              {t('activePositions')}
            </p>
          </div>
        </div>

        <div className="border-t border-[var(--border)] pt-3 text-sm text-[var(--foreground-muted)]">
          {t('totalInvestment', { amount: formatCurrency(summary.total_investment, summary.currency) })}
        </div>
      </div>
    </Card>
  );
}
