'use client';

import { useCallback, useMemo, useState } from 'react';
import { CalendarIcon, RotateCcw } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { format, parse } from 'date-fns';
import { ko, enUS, zhCN } from 'react-day-picker/locale';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface DateSelectorProps {
  /** null means "today" (latest available data) */
  value: string | null;
  onChange: (date: string | null) => void;
  disabled?: boolean;
}

const LOCALE_MAP: Record<string, typeof ko> = {
  ko,
  en: enUS,
  zh: zhCN,
};

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
  const [open, setOpen] = useState(false);

  const selectedDate = useMemo(() => {
    const dateStr = value ?? today;
    return parse(dateStr, 'yyyy-MM-dd', new Date());
  }, [value, today]);

  const todayDate = useMemo(() => new Date(), []);
  const calendarLocale = LOCALE_MAP[locale] ?? enUS;

  const handleSelect = useCallback(
    (date: Date | undefined) => {
      if (!date) return;
      const formatted = format(date, 'yyyy-MM-dd');
      onChange(formatted === today ? null : formatted);
      setOpen(false);
    },
    [onChange, today]
  );

  const handleResetToToday = useCallback(() => {
    onChange(null);
  }, [onChange]);

  const displayText = useMemo(() => {
    return format(selectedDate, 'PPP', { locale: calendarLocale });
  }, [selectedDate, calendarLocale]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger
            disabled={disabled}
            className={`flex-1 flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-left transition-colors cursor-pointer
              focus:border-[var(--color-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/20
              disabled:cursor-not-allowed disabled:opacity-50
              ${isToday ? 'text-[var(--foreground-muted)]' : 'text-[var(--foreground)]'}`}
          >
            <CalendarIcon className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" />
            <span className="truncate">{displayText}</span>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={handleSelect}
              locale={calendarLocale}
              disabled={{ after: todayDate }}
              defaultMonth={selectedDate}
            />
          </PopoverContent>
        </Popover>
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
