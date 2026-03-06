'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import { getExecutions } from '@/lib/api';
import type { ExecutionHistorySummary } from '@/lib/types';
import { History, ArrowRight, Layers } from 'lucide-react';
import { Link } from '@/i18n/navigation';

interface LoadingState {
  loading: boolean;
  error: string | null;
}

function formatRelativeDate(
  dateStr: string,
  t: ReturnType<typeof useTranslations>
): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diffMs = todayStart.getTime() - new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return t('dateToday');
    if (diffDays === 1) return t('dateYesterday');
    return t('dateDaysAgo', { days: diffDays });
  } catch {
    return dateStr;
  }
}

export default function RecentExecutionsCard() {
  const t = useTranslations('dashboard');
  const tReports = useTranslations('reports');
  const [items, setItems] = useState<ExecutionHistorySummary[]>([]);
  const [state, setState] = useState<LoadingState>({ loading: true, error: null });

  useEffect(() => {
    const fetchExecutions = async () => {
      try {
        const data = await getExecutions({ limit: 10 });
        setItems(data.items);
        setState({ loading: false, error: null });
      } catch (err) {
        setState({
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to load executions',
        });
      }
    };

    fetchExecutions();
  }, []);

  if (state.loading) {
    return (
      <Card title={t('recentExecutions')}>
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
      <Card title={t('recentExecutions')}>
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <History className="h-5 w-5" />
          <span>{t('unableToLoadExecutions')}</span>
        </div>
        <p className="mt-2 text-sm text-red-500">{state.error}</p>
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card title={t('recentExecutions')}>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <History className="mb-3 h-10 w-10 text-[var(--foreground-muted)]" />
          <p className="text-[var(--foreground-muted)]">{t('noExecutions')}</p>
          <p className="mt-1 text-sm text-[var(--foreground-muted)]">
            {t('runScreeningForExecutions')}
          </p>
        </div>
      </Card>
    );
  }

  // Group items by execution_type + preset/name, keeping the most recent as representative
  const grouped = items.reduce<Array<{ key: string; representative: ExecutionHistorySummary; count: number }>>((acc, item) => {
    const key = `${item.execution_type}::${item.name || item.preset}`;
    const existing = acc.find((g) => g.key === key);
    if (existing) {
      existing.count += 1;
      if (new Date(item.created_at) > new Date(existing.representative.created_at)) {
        existing.representative = item;
      }
    } else {
      acc.push({ key, representative: item, count: 1 });
    }
    return acc;
  }, []);

  return (
    <Card title={t('recentExecutions')} padding="none">
      <div className="divide-y divide-[var(--border)]">
        {grouped.map(({ representative: item, count }) => (
          <Link
            key={item.id}
            href={`/reports/${item.id}`}
            className="flex items-center gap-4 px-6 py-4 hover:bg-[var(--background)] transition-colors group"
          >
            <div className="flex-shrink-0">
              {item.execution_type === 'screening' ? (
                <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                  {tReports('screening')}
                </span>
              ) : (
                <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-800 dark:bg-purple-900/40 dark:text-purple-300">
                  {tReports('strategy')}
                </span>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-[var(--foreground)] truncate">
                  {item.name || item.preset}
                </span>
                {count > 1 && (
                  <span className="inline-flex items-center gap-0.5 rounded-full bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[10px] font-medium text-[var(--foreground-muted)]">
                    <Layers className="h-2.5 w-2.5" />
                    {count}
                  </span>
                )}
              </div>
              <div className="mt-1 flex items-center gap-2 text-sm text-[var(--foreground-muted)]">
                <span>
                  <span className="font-semibold text-green-600 dark:text-green-400">
                    {item.matched_count}
                  </span>
                  {' / '}
                  {item.total_count}
                </span>
                {item.reference_date && (
                  <span className="text-xs">{item.reference_date}</span>
                )}
                <span>{formatRelativeDate(item.created_at, tReports)}</span>
              </div>
            </div>

            <ArrowRight className="h-4 w-4 text-[var(--foreground-muted)] group-hover:text-[var(--color-primary)] transition-colors" />
          </Link>
        ))}

        <Link
          href="/reports"
          className="flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium text-[var(--color-primary)] hover:bg-[var(--background)] transition-colors"
        >
          {t('viewAllExecutions')}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
}
