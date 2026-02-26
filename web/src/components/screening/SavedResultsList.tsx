'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Trash2, FolderOpen, Inbox } from 'lucide-react';
import { useSavedScreeningResults, useDeleteScreeningResult } from '@/hooks/useScreening';
import { getSavedScreeningResult } from '@/lib/api';
import type { ScreeningResult } from '@/lib/types';

interface SavedResultsListProps {
  onLoad: (data: {
    results: ScreeningResult[];
    preset: string;
    universes: string[];
    referenceDate: string | null;
    totalCount: number;
    matchedCount: number;
    elapsedMs: number | null;
  }) => void;
}

export default function SavedResultsList({ onLoad }: SavedResultsListProps) {
  const t = useTranslations('screening');
  const { data, isLoading } = useSavedScreeningResults();
  const deleteMutation = useDeleteScreeningResult();
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const [loadError, setLoadError] = useState<string | null>(null);

  const handleLoad = async (id: string) => {
    setLoadingId(id);
    setLoadError(null);
    try {
      const full = await getSavedScreeningResult(id);
      onLoad({
        results: full.results,
        preset: full.preset,
        universes: full.universes,
        referenceDate: full.reference_date ?? null,
        totalCount: full.total_count,
        matchedCount: full.matched_count,
        elapsedMs: full.elapsed_ms ?? null,
      });
    } catch (err) {
      console.error('Failed to load saved result:', err);
      setLoadError(err instanceof Error ? err.message : 'Failed to load result');
    } finally {
      setLoadingId(null);
    }
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => setConfirmDeleteId(null),
    });
  };

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--color-primary)]" />
      </div>
    );
  }

  const items = data?.results ?? [];

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-8">
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <Inbox className="h-10 w-10 text-[var(--foreground-muted)]" />
          <p className="text-lg font-semibold text-[var(--foreground)]">{t('noSavedResults')}</p>
          <p className="text-sm text-[var(--foreground-muted)]">{t('noSavedResultsDesc')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {loadError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {loadError}
        </div>
      )}
      {items.map((item) => (
        <div
          key={item.id}
          className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-4 transition-colors hover:border-[var(--color-primary)]/30"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h4 className="truncate font-medium text-[var(--foreground)]">{item.name}</h4>
              {item.description && (
                <p className="mt-0.5 truncate text-xs text-[var(--foreground-muted)]">
                  {item.description}
                </p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--foreground-muted)]">
                <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 font-medium text-[var(--color-primary)]">
                  {item.preset}
                </span>
                {item.universes.map((u) => (
                  <span
                    key={u}
                    className="rounded-full bg-[var(--background)] border border-[var(--border)] px-2 py-0.5"
                  >
                    {u}
                  </span>
                ))}
                <span>
                  {item.matched_count}/{item.total_count} {t('matched').replace(':', '').trim()}
                </span>
                <span>
                  {t('savedOn')}: {new Date(item.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => handleLoad(item.id)}
                disabled={loadingId === item.id}
                className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--background)] px-2.5 py-1.5 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--border)]/50 transition-colors disabled:opacity-50"
              >
                <FolderOpen className="h-3.5 w-3.5" />
                {loadingId === item.id ? '...' : t('loadResult')}
              </button>
              {confirmDeleteId === item.id ? (
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => handleDelete(item.id)}
                    disabled={deleteMutation.isPending}
                    className="rounded-md bg-red-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50"
                  >
                    {t('yes')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteId(null)}
                    className="rounded-md border border-[var(--border)] bg-[var(--background)] px-2.5 py-1.5 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--border)]/50 transition-colors"
                  >
                    {t('no')}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmDeleteId(item.id)}
                  className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--background)] px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  {t('deleteResult')}
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
