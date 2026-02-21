'use client';

import { useTranslations } from 'next-intl';
import { CheckCircle, XCircle } from 'lucide-react';
import type { ConditionResult } from '@/lib/types';

interface ConditionDetailsProps {
  /** List of condition results to display */
  conditions: ConditionResult[];
}

/**
 * Displays detailed condition results with pass/fail indicators
 */
export default function ConditionDetails({ conditions }: ConditionDetailsProps) {
  const t = useTranslations('screening');
  const tc = useTranslations('conditions');

  if (conditions.length === 0) {
    return (
      <p className="text-sm text-[var(--foreground-muted)]">
        {t('noConditions')}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {conditions.map((condition, index) => (
        <div
          key={`${condition.condition_name}-${index}`}
          className={`
            rounded-lg border p-3
            ${
              condition.matched
                ? 'border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950'
                : 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950'
            }
          `}
        >
          <div className="flex items-center gap-2">
            {condition.matched ? (
              <CheckCircle className="h-5 w-5 flex-shrink-0 text-green-600 dark:text-green-400" />
            ) : (
              <XCircle className="h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400" />
            )}
            <span
              className={`font-medium ${
                condition.matched
                  ? 'text-green-800 dark:text-green-200'
                  : 'text-red-800 dark:text-red-200'
              }`}
            >
              {tc.has(`${condition.condition_name}.label`)
                ? tc(`${condition.condition_name}.label`)
                : condition.condition_name
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (l) => l.toUpperCase())}
            </span>
          </div>

          {Object.keys(condition.details).length > 0 && (
            <div className="mt-2 ml-7">
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                {Object.entries(condition.details).map(([key, value]) => (
                  <div key={key} className="contents">
                    <dt className="text-[var(--foreground-muted)]">{key}:</dt>
                    <dd
                      className={`font-mono ${
                        condition.matched
                          ? 'text-green-700 dark:text-green-300'
                          : 'text-red-700 dark:text-red-300'
                      }`}
                    >
                      {formatValue(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/**
 * Format a value for display
 */
function formatValue(value: unknown): string {
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
    return value ? 'Yes' : 'No';
  }
  return String(value);
}
