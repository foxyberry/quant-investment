'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { ResultTable } from '@/components/screening';
import { getExecution } from '@/lib/api';
import type { ExecutionHistoryDetail, ScreeningResult } from '@/lib/types';
import {
  ArrowLeft,
  Clock,
  RefreshCw,
  Play,
} from 'lucide-react';

function formatElapsed(ms: number | null | undefined): string {
  if (ms == null) return '-';
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
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

function mapToScreeningResults(
  results: Array<Record<string, unknown>>
): ScreeningResult[] {
  return results.map((r) => ({
    ticker: (r.ticker as string) ?? '',
    name: (r.name as string) ?? '',
    current_price: (r.current_price as number | null) ?? null,
    market: (r.market as string | null) ?? null,
    change_pct: (r.change_pct as number | null) ?? null,
    volume: (r.volume as number | null) ?? null,
    score: (r.score as number | null) ?? null,
    matched: (r.matched as boolean) ?? false,
    conditions: Array.isArray(r.conditions)
      ? r.conditions.map((c: Record<string, unknown>) => ({
          condition_name: (c.condition_name as string) ?? '',
          matched: (c.matched as boolean) ?? false,
          details: (c.details as Record<string, unknown>) ?? {},
        }))
      : [],
  }));
}

export default function ExecutionDetailPage() {
  const t = useTranslations('reports');
  const params = useParams();
  const id = params.id as string;

  const [execution, setExecution] = useState<ExecutionHistoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getExecution(id);
        setExecution(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('failedToLoad'));
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [id, t]);

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <BackLink t={t} />
        <div className="space-y-4 animate-pulse">
          <div className="h-10 w-64 rounded bg-[var(--border)]" />
          <div className="h-16 rounded-lg bg-[var(--border)]" />
          <div className="h-64 rounded-lg bg-[var(--border)]" />
        </div>
      </div>
    );
  }

  // Error state
  if (error || !execution) {
    return (
      <div className="space-y-6">
        <BackLink t={t} />
        <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] py-12">
          <p className="text-[var(--foreground-muted)]">{t('failedToLoad')}</p>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            {t('retry')}
          </button>
        </div>
      </div>
    );
  }

  const screeningResults = mapToScreeningResults(execution.results);
  const rerunHref =
    execution.execution_type === 'strategy' ? '/strategy' : '/screening';

  return (
    <div className="space-y-6">
      {/* Back link */}
      <BackLink t={t} />

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <TypeBadge type={execution.execution_type} t={t} />
            <h1 className="text-2xl font-bold text-[var(--foreground)]">
              {execution.name || execution.preset}
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {execution.universes.map((universe) => (
              <span
                key={universe}
                className="inline-flex items-center rounded-full bg-[var(--color-primary)]/10 px-2.5 py-0.5 text-xs font-medium text-[var(--color-primary)]"
              >
                {universe}
              </span>
            ))}
            {execution.reference_date && (
              <span className="inline-flex items-center rounded-full bg-[var(--background)] border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--foreground-muted)]">
                {execution.reference_date}
              </span>
            )}
            <span className="text-sm text-[var(--foreground-muted)]">
              {formatRelativeDate(execution.created_at, t)}
            </span>
          </div>
        </div>

        {/* Rerun button */}
        <Link
          href={rerunHref}
          className="inline-flex items-center gap-2 rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
        >
          <Play className="h-4 w-4" />
          {t('rerun')}
        </Link>
      </div>

      {/* Stats bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--foreground-muted)]">
            {t('totalCount')}
          </span>
          <span className="font-semibold text-[var(--foreground)]">
            {execution.total_count.toLocaleString()}
          </span>
        </div>
        <div className="h-4 w-px bg-[var(--border)]" />
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--foreground-muted)]">
            {t('matchedCount')}
          </span>
          <span className="font-semibold text-green-600 dark:text-green-400">
            {execution.matched_count.toLocaleString()}
          </span>
        </div>
        <div className="h-4 w-px bg-[var(--border)]" />
        <div className="flex items-center gap-2">
          <span className="text-sm text-[var(--foreground-muted)]">
            {t('matchRate')}
          </span>
          <span className="font-semibold text-[var(--foreground)]">
            {execution.total_count > 0
              ? ((execution.matched_count / execution.total_count) * 100).toFixed(1)
              : '0'}
            %
          </span>
        </div>
        {execution.elapsed_ms != null && (
          <>
            <div className="h-4 w-px bg-[var(--border)]" />
            <div className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-[var(--foreground-muted)]" />
              <span className="text-sm text-[var(--foreground-muted)]">
                {t('executionTime')}
              </span>
              <span className="font-semibold text-[var(--foreground)]">
                {formatElapsed(execution.elapsed_ms)}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Results table */}
      <ResultTable results={screeningResults} hasRun />
    </div>
  );
}

/* ----------- Sub-components ----------- */

function BackLink({ t }: { t: ReturnType<typeof useTranslations> }) {
  return (
    <Link
      href="/reports"
      className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-primary)] hover:opacity-80 transition-opacity"
    >
      <ArrowLeft className="h-4 w-4" />
      {t('back')}
    </Link>
  );
}

function TypeBadge({
  type,
  t,
}: {
  type: 'screening' | 'strategy';
  t: ReturnType<typeof useTranslations>;
}) {
  if (type === 'screening') {
    return (
      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
        {t('screening')}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800 dark:bg-purple-900/40 dark:text-purple-300">
      {t('strategy')}
    </span>
  );
}
