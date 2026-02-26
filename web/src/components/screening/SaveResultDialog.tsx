'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X, Save } from 'lucide-react';
import { useSaveScreeningResult } from '@/hooks/useScreening';
import type { ScreeningResult } from '@/lib/types';

interface SaveResultDialogProps {
  open: boolean;
  onClose: () => void;
  preset: string;
  universes: string[];
  referenceDate: string | null;
  totalCount: number;
  matchedCount: number;
  elapsedMs: number | null;
  results: ScreeningResult[];
}

export default function SaveResultDialog({
  open,
  onClose,
  preset,
  universes,
  referenceDate,
  totalCount,
  matchedCount,
  elapsedMs,
  results,
}: SaveResultDialogProps) {
  const t = useTranslations('screening');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const saveMutation = useSaveScreeningResult();

  if (!open) return null;

  const handleSave = () => {
    if (!name.trim()) return;
    saveMutation.mutate(
      {
        name: name.trim(),
        description: description.trim() || undefined,
        preset,
        universes,
        reference_date: referenceDate,
        total_count: totalCount,
        matched_count: matchedCount,
        elapsed_ms: elapsedMs,
        results,
      },
      {
        onSuccess: () => {
          setName('');
          setDescription('');
          onClose();
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <button type="button" className="absolute inset-0" onClick={onClose} aria-label="Close" />
      <div className="relative z-10 w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">{t('saveResult')}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--background)] hover:text-[var(--foreground)]"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 p-4">
          {/* Summary */}
          <div className="flex flex-wrap gap-2 text-xs text-[var(--foreground-muted)]">
            <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 font-medium text-[var(--color-primary)]">
              {preset}
            </span>
            {universes.map((u) => (
              <span
                key={u}
                className="rounded-full bg-[var(--background)] border border-[var(--border)] px-2 py-0.5"
              >
                {u}
              </span>
            ))}
            <span className="rounded-full bg-[var(--background)] border border-[var(--border)] px-2 py-0.5">
              {matchedCount}/{totalCount} {t('matched').replace(':', '').trim()}
            </span>
          </div>

          {/* Name input */}
          <div>
            <label className="mb-1 block text-xs font-medium text-[var(--foreground)]">
              {t('saveResultName')}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('saveResultNamePlaceholder')}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder-[var(--foreground-muted)] focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
              autoFocus
            />
          </div>

          {/* Description input */}
          <div>
            <label className="mb-1 block text-xs font-medium text-[var(--foreground)]">
              {t('saveResultDescription')}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('saveResultDescriptionPlaceholder')}
              rows={2}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder-[var(--foreground-muted)] focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)] resize-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-[var(--border)] px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
          >
            {t('cancel')}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!name.trim() || saveMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="h-3.5 w-3.5" />
            {saveMutation.isPending ? t('saving') : t('saveResult')}
          </button>
        </div>
      </div>
    </div>
  );
}
