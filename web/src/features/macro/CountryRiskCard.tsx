'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import { useCountryRisk } from '@/hooks/useMarket';
import { ShieldAlert, TrendingDown, TrendingUp, Minus } from 'lucide-react';

const RISK_COLOR: Record<string, string> = {
  low: 'text-green-500',
  moderate: 'text-yellow-500',
  high: 'text-orange-500',
  critical: 'text-red-500',
};

const RISK_BG: Record<string, string> = {
  low: 'bg-green-500/10',
  moderate: 'bg-yellow-500/10',
  high: 'bg-orange-500/10',
  critical: 'bg-red-500/10',
};

const TREND_ICON = {
  improving: TrendingDown,
  deteriorating: TrendingUp,
  stable: Minus,
};

const DEFAULT_COUNTRIES = ['KR', 'US', 'CN', 'JP'] as const;

export default function CountryRiskCard() {
  const t = useTranslations('macro');
  const [selected, setSelected] = useState<string>('KR');
  const { data, isLoading } = useCountryRisk(selected);

  if (isLoading) {
    return (
      <Card className="animate-pulse p-4">
        <div className="h-6 w-40 rounded bg-[var(--background-secondary)]" />
        <div className="mt-3 h-32 rounded bg-[var(--background-secondary)]" />
      </Card>
    );
  }

  if (!data?.available) {
    return (
      <Card className="p-4">
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <ShieldAlert className="h-5 w-5" />
          <span>{t('worldmonitorUnavailable')}</span>
        </div>
      </Card>
    );
  }

  const riskClass = RISK_COLOR[data.risk_level ?? ''] ?? '';
  const riskBg = RISK_BG[data.risk_level ?? ''] ?? '';

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <ShieldAlert className="h-5 w-5 text-[var(--accent)]" />
          {t('countryRisk')}
        </h3>
        <div className="flex gap-1">
          {DEFAULT_COUNTRIES.map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => setSelected(code)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                selected === code
                  ? 'bg-[var(--accent)] text-white'
                  : 'bg-[var(--background-secondary)] text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
              }`}
            >
              {code}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3">
        <div className="flex items-center gap-3">
          <div className={`rounded-lg px-3 py-2 ${riskBg}`}>
            <span className="text-2xl font-bold tabular-nums">
              {data.overall_score != null ? data.overall_score.toFixed(0) : '-'}
            </span>
            <span className="text-xs text-[var(--foreground-muted)]">/100</span>
          </div>
          <div>
            <p className="text-sm font-medium">
              {data.country_name ?? data.country_code}
            </p>
            {data.risk_level && (
              <p className={`text-xs font-semibold uppercase ${riskClass}`}>
                {data.risk_level}
              </p>
            )}
          </div>
        </div>

        {data.signals.length > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {data.signals.map((sig, i) => {
              const TrendIcon = TREND_ICON[sig.trend as keyof typeof TREND_ICON] ?? Minus;
              return (
                <div key={i} className="rounded border border-[var(--border)] px-2 py-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-[var(--foreground-muted)] truncate">{sig.category}</span>
                    <TrendIcon className="h-3 w-3 text-[var(--foreground-muted)]" />
                  </div>
                  <span className="text-sm font-semibold tabular-nums">
                    {sig.score != null ? sig.score.toFixed(0) : '-'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}
