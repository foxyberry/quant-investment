'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import { getReports } from '@/lib/api';
import type { ReportSummary } from '@/lib/types';
import { FileText, Calendar, TrendingUp, ArrowRight } from 'lucide-react';
import { Link } from '@/i18n/navigation';

interface LoadingState {
  loading: boolean;
  error: string | null;
}

export default function RecentReportsCard() {
  const t = useTranslations('dashboard');
  const tMarkets = useTranslations('markets');
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [state, setState] = useState<LoadingState>({ loading: true, error: null });

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const data = await getReports(3);
        setReports(data);
        setState({ loading: false, error: null });
      } catch (err) {
        setState({
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to load reports',
        });
      }
    };

    fetchReports();
  }, []);

  const formatDate = (dateStr: string) => {
    try {
      const year = dateStr.slice(0, 4);
      const month = dateStr.slice(4, 6);
      const day = dateStr.slice(6, 8);
      const date = new Date(`${year}-${month}-${day}`);
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(date);
    } catch {
      return dateStr;
    }
  };

  const getMarketLabel = (market: string) => {
    const key = market.toLowerCase();
    try {
      return tMarkets(key);
    } catch {
      return market.toUpperCase();
    }
  };

  if (state.loading) {
    return (
      <Card title={t('recentReports')}>
        <div className="space-y-3 animate-pulse">
          <div className="h-16 rounded bg-[var(--border)]" />
          <div className="h-16 rounded bg-[var(--border)]" />
          <div className="h-16 rounded bg-[var(--border)]" />
        </div>
      </Card>
    );
  }

  if (state.error) {
    return (
      <Card title={t('recentReports')}>
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <FileText className="h-5 w-5" />
          <span>{t('unableToLoadReports')}</span>
        </div>
        <p className="mt-2 text-sm text-red-500">{state.error}</p>
      </Card>
    );
  }

  if (reports.length === 0) {
    return (
      <Card title={t('recentReports')}>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <FileText className="mb-3 h-10 w-10 text-[var(--foreground-muted)]" />
          <p className="text-[var(--foreground-muted)]">{t('noReports')}</p>
          <p className="mt-1 text-sm text-[var(--foreground-muted)]">
            {t('runScreeningForReports')}
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card title={t('recentReports')} padding="none">
      <div className="divide-y divide-[var(--border)]">
        {reports.map((report, index) => (
          <Link
            key={`${report.date}-${report.market}-${index}`}
            href={`/analysis/reports/${report.date}`}
            className="flex items-center gap-4 px-6 py-4 hover:bg-[var(--background)] transition-colors group"
          >
            <div className="flex-shrink-0 rounded-lg bg-[var(--background)] p-2">
              <FileText className="h-5 w-5 text-[var(--color-primary)]" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-[var(--foreground)]">
                  {getMarketLabel(report.market)}
                </span>
                {report.buy_count > 0 && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                    <TrendingUp className="h-3 w-3" />
                    {report.buy_count} {t('buy')}
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
                <Calendar className="h-3 w-3" />
                <span>{formatDate(report.date)}</span>
              </div>
            </div>

            <ArrowRight className="h-4 w-4 text-[var(--foreground-muted)] group-hover:text-[var(--color-primary)] transition-colors" />
          </Link>
        ))}

        <Link
          href="/analysis"
          className="flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--background)] transition-colors"
        >
          {t('viewAllReports')}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
}
