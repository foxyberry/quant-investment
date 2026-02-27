'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { getExecutions, deleteExecution } from '@/lib/api';
import type { ExecutionHistorySummary } from '@/lib/types';
import {
  Trash2,
  ChevronRight,
  RefreshCw,
  Search,
  Filter,
} from 'lucide-react';

type FilterType = 'all' | 'screening' | 'strategy';

const PAGE_SIZE = 10;

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

export default function ExecutionHistoryList() {
  const t = useTranslations('reports');
  const [items, setItems] = useState<ExecutionHistorySummary[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const fetchData = useCallback(
    async (offset = 0, append = false) => {
      try {
        if (!append) setLoading(true);
        setError(null);

        const executionType = filter === 'all' ? undefined : filter;
        const data = await getExecutions({
          execution_type: executionType,
          limit: PAGE_SIZE,
          offset,
        });

        if (append) {
          setItems((prev) => [...prev, ...data.items]);
        } else {
          setItems(data.items);
        }
        setTotalCount(data.total_count);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : t('failedToLoad')
        );
      } finally {
        setLoading(false);
      }
    },
    [filter, t]
  );

  useEffect(() => {
    fetchData(0, false);
  }, [fetchData]);

  const handleLoadMore = () => {
    fetchData(items.length, true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteExecution(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      setTotalCount((prev) => prev - 1);
      setDeleteConfirmId(null);
    } catch {
      // Silently fail on delete error; the item remains in the list
    }
  };

  const handleFilterChange = (newFilter: FilterType) => {
    setFilter(newFilter);
  };

  // Loading skeleton
  if (loading && items.length === 0) {
    return (
      <div className="space-y-4">
        <FilterTabs filter={filter} onChange={handleFilterChange} t={t} />
        <div className="space-y-3 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]"
            />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error && items.length === 0) {
    return (
      <div className="space-y-4">
        <FilterTabs filter={filter} onChange={handleFilterChange} t={t} />
        <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] py-12">
          <p className="text-[var(--foreground-muted)]">{t('failedToLoad')}</p>
          <p className="text-sm text-red-500">{error}</p>
          <button
            type="button"
            onClick={() => fetchData(0, false)}
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            {t('retry')}
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (!loading && items.length === 0) {
    return (
      <div className="space-y-4">
        <FilterTabs filter={filter} onChange={handleFilterChange} t={t} />
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] py-12">
          <Search className="h-10 w-10 text-[var(--foreground-muted)]" />
          <p className="text-lg font-medium text-[var(--foreground)]">
            {t('noExecutions')}
          </p>
          <p className="text-sm text-[var(--foreground-muted)]">
            {t('runScreeningFirst')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <FilterTabs filter={filter} onChange={handleFilterChange} t={t} />

      {/* Execution count */}
      <p className="text-sm text-[var(--foreground-muted)]">
        {t('executionCount', { count: totalCount })}
      </p>

      {/* Items list */}
      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="group relative rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] transition-colors hover:border-[var(--color-primary)]/30"
          >
            <Link
              href={`/reports/${item.id}`}
              className="flex items-center gap-4 p-4"
            >
              {/* Type badge */}
              <div className="flex-shrink-0">
                <TypeBadge type={item.execution_type} t={t} />
              </div>

              {/* Content */}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-[var(--foreground)]">
                    {item.name || item.preset}
                  </span>
                  {/* Universe badges */}
                  {item.universes.map((universe) => (
                    <span
                      key={universe}
                      className="inline-flex items-center rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 text-[10px] font-medium text-[var(--color-primary)]"
                    >
                      {universe}
                    </span>
                  ))}
                </div>

                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-sm text-[var(--foreground-muted)]">
                  {/* Matched / Total */}
                  <span>
                    <span className="font-semibold text-green-600 dark:text-green-400">
                      {item.matched_count}
                    </span>
                    {' / '}
                    <span>{item.total_count}</span>
                  </span>

                  {/* Elapsed */}
                  {item.elapsed_ms != null && (
                    <span>{formatElapsed(item.elapsed_ms)}</span>
                  )}

                  {/* Relative date */}
                  <span>{formatRelativeDate(item.created_at, t)}</span>
                </div>
              </div>

              {/* Arrow */}
              <ChevronRight className="h-5 w-5 flex-shrink-0 text-[var(--foreground-muted)] group-hover:text-[var(--color-primary)] transition-colors" />
            </Link>

            {/* Delete button */}
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setDeleteConfirmId(item.id);
              }}
              className="absolute right-12 top-1/2 -translate-y-1/2 rounded p-1.5 text-[var(--foreground-muted)] opacity-0 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 group-hover:opacity-100 transition-all"
              aria-label="Delete"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Load more */}
      {items.length < totalCount && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleLoadMore}
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-6 py-2.5 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
          >
            {t('loadMore')}
          </button>
        </div>
      )}

      {/* Delete confirm dialog */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <button
            type="button"
            className="absolute inset-0"
            onClick={() => setDeleteConfirmId(null)}
            aria-label="Close"
          />
          <div className="relative z-10 w-full max-w-sm rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-6 shadow-2xl">
            <p className="text-[var(--foreground)]">
              {t('deleteConfirm')}
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteConfirmId(null)}
                className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
              >
                {t('back')}
              </button>
              <button
                type="button"
                onClick={() => handleDelete(deleteConfirmId)}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
              >
                <Trash2 className="mr-1.5 inline h-4 w-4" />
                {t('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ----------- Sub-components ----------- */

function FilterTabs({
  filter,
  onChange,
  t,
}: {
  filter: FilterType;
  onChange: (f: FilterType) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const tabs: { key: FilterType; label: string }[] = [
    { key: 'all', label: t('filterAll') },
    { key: 'screening', label: t('filterScreening') },
    { key: 'strategy', label: t('filterStrategy') },
  ];

  return (
    <div className="flex items-center gap-2">
      <Filter className="h-4 w-4 text-[var(--foreground-muted)]" />
      <div className="flex gap-1 rounded-lg bg-[var(--background)] p-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              filter === tab.key
                ? 'bg-[var(--background-secondary)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
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
