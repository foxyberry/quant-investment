'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { ResultTable } from '@/components/screening';
import { getExecution, updateExecution } from '@/lib/api';
import type { ExecutionHistoryDetail, ScreeningResult } from '@/lib/types';
import {
  ArrowLeft,
  CalendarDays,
  Clock,
  RefreshCw,
  Play,
  Database,
  CheckCircle,
  Pencil,
  PieChart,
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
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const nameInputRef = useRef<HTMLInputElement>(null);

  const handleNameSave = useCallback(async () => {
    if (!execution) return;
    const trimmed = editName.trim();
    setIsEditingName(false);
    if (!trimmed || trimmed === (execution.name || execution.preset)) return;
    try {
      const updated = await updateExecution(id, { name: trimmed });
      setExecution(updated);
    } catch {
      // Revert on failure — name stays as-is in UI
    }
  }, [execution, editName, id]);

  const startEditing = useCallback(() => {
    if (!execution) return;
    setEditName(execution.name || execution.preset || '');
    setIsEditingName(true);
    setTimeout(() => nameInputRef.current?.select(), 0);
  }, [execution]);

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
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-[72px] rounded-xl bg-[var(--border)]" />
            ))}
          </div>
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
    <div className="space-y-6 max-w-screen-2xl">
      {/* Back link */}
      <BackLink t={t} />

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <TypeBadge type={execution.execution_type} t={t} />
            {isEditingName ? (
              <input
                ref={nameInputRef}
                value={editName}
                onChange={e => setEditName(e.target.value)}
                onBlur={handleNameSave}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleNameSave();
                  if (e.key === 'Escape') setIsEditingName(false);
                }}
                className="text-2xl font-bold text-[var(--foreground)] bg-transparent border-b-2 border-[var(--color-primary)] outline-none px-0 py-0 w-full max-w-md"
              />
            ) : (
              <button
                type="button"
                onClick={startEditing}
                className="group flex items-center gap-2 text-2xl font-bold text-[var(--foreground)] hover:text-[var(--color-primary)] transition-colors"
                title="Click to edit"
              >
                {execution.name || execution.preset}
                <Pencil className="h-4 w-4 opacity-0 group-hover:opacity-50 transition-opacity" />
              </button>
            )}
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
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-300">
                <CalendarDays className="h-3 w-3" />
                {t('referenceDate')}: {execution.reference_date}
              </span>
            )}
            <span
              className="text-sm text-[var(--foreground-muted)]"
              title={new Date(execution.created_at).toLocaleString()}
            >
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

      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard
          icon={<CalendarDays className="h-5 w-5" />}
          label={t('referenceDate')}
          value={execution.reference_date ?? 'N/A'}
          accent={execution.reference_date ? 'amber' : undefined}
        />
        <StatCard
          icon={<Database className="h-5 w-5" />}
          label={t('totalCount')}
          value={execution.total_count.toLocaleString()}
        />
        <StatCard
          icon={<CheckCircle className="h-5 w-5" />}
          label={t('matchedCount')}
          value={execution.matched_count.toLocaleString()}
          accent="green"
        />
        <StatCard
          icon={<PieChart className="h-5 w-5" />}
          label={t('matchRate')}
          value={`${
            execution.total_count > 0
              ? ((execution.matched_count / execution.total_count) * 100).toFixed(1)
              : '0'
          }%`}
        />
        {execution.elapsed_ms != null && (
          <StatCard
            icon={<Clock className="h-5 w-5" />}
            label={t('executionTime')}
            value={formatElapsed(execution.elapsed_ms)}
          />
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

function StatCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  accent?: 'green' | 'amber';
}) {
  const valueColor =
    accent === 'green'
      ? 'text-green-600 dark:text-green-400'
      : accent === 'amber'
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-[var(--foreground)]';
  return (
    <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3 backdrop-blur-sm">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs text-[var(--foreground-muted)] truncate">
          {label}
        </p>
        <p className={`text-lg font-semibold tabular-nums ${valueColor}`}>
          {value}
        </p>
      </div>
    </div>
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
