'use client';

import { useTranslations } from 'next-intl';
import { useLocale } from 'next-intl';
import { CheckCircle2, XCircle, ExternalLink, Star } from 'lucide-react';
import type { ConditionResult } from '@/lib/types';

interface ConditionDetailsProps {
  /** List of condition results to display */
  conditions: ConditionResult[];
  /** Ticker symbol for action buttons */
  ticker?: string;
}

/** Keys to exclude when looking for the "actual" value in details */
const THRESHOLD_KEY_PREFIXES = ['min_', 'max_'];
const EXCLUDED_KEYS = ['error', 'timestamp', 'matched'];

/**
 * Extract the first numeric "actual" value from a condition's details map,
 * ignoring threshold keys (min_*, max_*) and metadata keys.
 */
function extractActualValue(details: Record<string, unknown>): number | null {
  for (const [key, value] of Object.entries(details)) {
    if (EXCLUDED_KEYS.includes(key)) continue;
    if (THRESHOLD_KEY_PREFIXES.some((p) => key.startsWith(p))) continue;
    if (typeof value === 'number') return value;
  }
  return null;
}

/**
 * Extract threshold information from details (min_* or max_* keys).
 * Returns { operator, value } or null.
 */
function extractThreshold(
  details: Record<string, unknown>,
): { operator: string; value: number } | null {
  for (const [key, value] of Object.entries(details)) {
    if (typeof value !== 'number') continue;
    if (key.startsWith('min_')) return { operator: '\u2265', value }; // >=
    if (key.startsWith('max_')) return { operator: '\u2264', value }; // <=
  }
  return null;
}

/**
 * Displays detailed condition results with pass/fail indicators,
 * a summary progress bar, and action buttons.
 */
export default function ConditionDetails({
  conditions,
  ticker,
}: ConditionDetailsProps) {
  const t = useTranslations('screening');
  const tConditions = useTranslations('conditions');
  const locale = useLocale();

  if (conditions.length === 0) {
    return (
      <p className="text-sm text-[var(--foreground-muted)]">
        {t('noConditions')}
      </p>
    );
  }

  const total = conditions.length;
  const passed = conditions.filter((c) => c.matched).length;
  const rate = Math.round((passed / total) * 100);

  function handleViewFullDetail() {
    if (!ticker) return;
    const width = 900;
    const height = 700;
    const left = Math.round(window.screenX + (window.outerWidth - width) / 2);
    const top = Math.round(window.screenY + (window.outerHeight - height) / 2);
    window.open(
      `/${locale}/analysis/${ticker}?popup=true`,
      `analysis_${ticker}`,
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`,
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-4">
      {/* --- Summary bar --- */}
      <div className="mb-4 flex items-center gap-3">
        <span className="shrink-0 text-sm font-medium text-[var(--foreground)]">
          {t('conditionMatchSummary', {
            passed: String(passed),
            total: String(total),
            rate: String(rate),
          })}
        </span>
        <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-[var(--border)]">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-green-500 transition-all duration-300"
            style={{ width: `${rate}%` }}
          />
        </div>
      </div>

      {/* --- Condition rows --- */}
      <div className="divide-y divide-[var(--border)]">
        {conditions.map((condition, index) => {
          const actual = extractActualValue(condition.details);
          const threshold = extractThreshold(condition.details);
          const conditionI18nKey = `${condition.condition_name}.label`;
          const conditionLabel = tConditions.has(conditionI18nKey)
            ? tConditions(conditionI18nKey as never)
            : condition.condition_name
                .replace(/_/g, ' ')
                .replace(/\./g, ' ')
                .replace(/\b\w/g, (char) => char.toUpperCase());

          return (
            <div
              key={`${condition.condition_name}-${index}`}
              className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0"
            >
              {/* Left: icon + name */}
              <div className="flex min-w-0 items-center gap-2">
                {condition.matched ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600 dark:text-green-400" />
                ) : (
                  <XCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
                )}
                <span className="truncate text-sm font-medium text-[var(--foreground)]">
                  {conditionLabel}
                </span>
              </div>

              {/* Center: actual vs threshold */}
              <div className="hidden items-center gap-2 text-xs text-[var(--foreground-muted)] sm:flex">
                {actual !== null && (
                  <span className="font-mono">
                    {t('actualValue')}: {formatValue(actual, t('yes'), t('no'))}
                  </span>
                )}
                {actual !== null && threshold !== null && (
                  <span className="text-[var(--border)]">/</span>
                )}
                {threshold !== null && (
                  <span className="font-mono">
                    {t('targetValue')}: {threshold.operator}{' '}
                    {formatValue(threshold.value, t('yes'), t('no'))}
                  </span>
                )}
              </div>

              {/* Right: pass/fail badge */}
              {condition.matched ? (
                <span className="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-bold text-green-700 dark:bg-green-500/10 dark:text-green-400">
                  {t('passLabel')}
                </span>
              ) : (
                <span className="shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold text-red-700 dark:bg-red-500/10 dark:text-red-400">
                  {t('failLabel')}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* --- Action buttons --- */}
      {ticker && (
        <div className="mt-4 flex items-center gap-2 border-t border-[var(--border)] pt-3">
          <button
            type="button"
            onClick={handleViewFullDetail}
            className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] transition-colors hover:bg-[var(--background-hover)]"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            {t('viewFullDetail')}
          </button>
          <button
            type="button"
            disabled
            className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-md border border-[var(--border)] px-3 py-1.5 text-xs font-medium text-[var(--foreground-muted)] opacity-50"
          >
            <Star className="h-3.5 w-3.5" />
            {t('addToWatchlist')}
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Format a value for display
 */
function formatValue(
  value: unknown,
  yesLabel: string,
  noLabel: string,
): string {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'number') {
    // Format numbers with appropriate precision
    if (Number.isInteger(value)) {
      return value.toLocaleString();
    }
    return value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    });
  }
  if (typeof value === 'boolean') {
    return value ? yesLabel : noLabel;
  }
  return String(value);
}
