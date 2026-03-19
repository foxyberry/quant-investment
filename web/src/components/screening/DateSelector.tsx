'use client';

import { useCallback, useMemo } from 'react';
import { RotateCcw } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';

interface DateSelectorProps {
  /** null means "today" (latest available data) */
  value: string | null;
  onChange: (date: string | null) => void;
  disabled?: boolean;
}

function getTodayString(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export default function DateSelector({
  value,
  onChange,
  disabled = false,
}: DateSelectorProps) {
  const t = useTranslations('screening');
  const locale = useLocale();
  const today = useMemo(() => getTodayString(), []);
  const isToday = value === null;

  const handleDateChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newDate = e.target.value;
      // If the selected date equals today, treat as null (latest)
      onChange(newDate === today ? null : newDate || null);
    },
    [onChange, today]
  );

  const handleResetToToday = useCallback(() => {
    onChange(null);
  }, [onChange]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <input
          type="date"
          lang={locale}
          value={value ?? today}
          max={today}
          onChange={handleDateChange}
          disabled={disabled}
          className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-[var(--color-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/20 disabled:cursor-not-allowed disabled:opacity-50"
        />
        {!isToday && (
          <button
            type="button"
            onClick={handleResetToToday}
            disabled={disabled}
            className="flex items-center gap-1 rounded-lg border border-[var(--border)] bg-[var(--background)] px-2.5 py-2 text-sm text-[var(--foreground-muted)] hover:text-[var(--foreground)] hover:border-[var(--color-primary)]/50 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            title={t('resetToToday')}
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {isToday && (
        <p className="text-xs text-[var(--foreground-muted)]">
          {t('usingLatestData')}
        </p>
      )}
    </div>
  );
}
