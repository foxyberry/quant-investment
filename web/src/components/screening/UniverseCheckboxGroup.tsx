'use client';

import { useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  SUPPORTED_UNIVERSES,
  type SupportedUniverse,
} from '@/lib/strategy/graphSerializer';

interface UniverseCheckboxGroupProps {
  selectedUniverses: string[];
  onChange: (universes: string[]) => void;
  stockCounts?: Record<string, number>;
  disabled?: boolean;
}

export default function UniverseCheckboxGroup({
  selectedUniverses,
  onChange,
  stockCounts,
  disabled = false,
}: UniverseCheckboxGroupProps) {
  const t = useTranslations('screening');

  const handleToggle = useCallback(
    (universe: SupportedUniverse) => {
      const exists = selectedUniverses.includes(universe);
      if (exists) {
        // Enforce "at least one selected"
        if (selectedUniverses.length === 1) return;
        onChange(selectedUniverses.filter((u) => u !== universe));
      } else {
        onChange([...selectedUniverses, universe]);
      }
    },
    [selectedUniverses, onChange]
  );

  return (
    <div className="space-y-1.5">
      {SUPPORTED_UNIVERSES.map((universe) => {
        const isSelected = selectedUniverses.includes(universe);
        const count = stockCounts?.[universe];

        return (
          <label
            key={universe}
            className={`flex items-center gap-2.5 rounded-md border px-3 py-2 text-sm transition-colors cursor-pointer ${
              isSelected
                ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/5 text-[var(--foreground)]'
                : 'border-[var(--border)] bg-[var(--background)] text-[var(--foreground-muted)]'
            } ${disabled ? 'cursor-not-allowed opacity-50' : 'hover:border-[var(--color-primary)]/50'}`}
          >
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => handleToggle(universe)}
              disabled={disabled}
              className="rounded border-[var(--border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]/20"
            />
            <span className="flex-1 font-medium">{universe}</span>
            {count !== undefined && (
              <span className="text-xs text-[var(--foreground-muted)]">
                {count.toLocaleString()} {t('stocks')}
              </span>
            )}
          </label>
        );
      })}
    </div>
  );
}
