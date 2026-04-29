'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import { useMarketRadar } from '@/hooks/useMarket';
import { Radio, TrendingDown, TrendingUp, Minus } from 'lucide-react';

export default function MarketRadarCard() {
  const t = useTranslations('macro');
  const { data, isLoading } = useMarketRadar();

  if (isLoading) {
    return (
      <Card className="animate-pulse p-4">
        <div className="h-6 w-40 rounded bg-[var(--background-secondary)]" />
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-16 rounded bg-[var(--background-secondary)]" />
          ))}
        </div>
      </Card>
    );
  }

  if (!data?.available) {
    return (
      <Card className="p-4">
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <Radio className="h-5 w-5" />
          <span>{t('worldmonitorUnavailable')}</span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <Radio className="h-5 w-5 text-[var(--accent)]" />
          {t('marketRadar')}
        </h3>
        {data.updated_at && (
          <span className="text-xs text-[var(--foreground-muted)]">
            {new Date(data.updated_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      {data.exchanges.length > 0 && (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {data.exchanges.map((ex, i) => {
            const pct = ex.change_pct;
            const isUp = pct != null && pct > 0;
            const isDown = pct != null && pct < 0;
            return (
              <div
                key={i}
                className="rounded-lg border border-[var(--border)] p-2.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium truncate" title={ex.name ?? undefined}>
                    {ex.index ?? ex.name ?? '-'}
                  </span>
                  {ex.status && (
                    <span className={`text-[10px] ${ex.status === 'open' ? 'text-green-500' : 'text-[var(--foreground-muted)]'}`}>
                      {ex.status}
                    </span>
                  )}
                </div>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-sm font-semibold tabular-nums">
                    {ex.value != null ? ex.value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '-'}
                  </span>
                  {pct != null && (
                    <span className={`flex items-center gap-0.5 text-xs font-medium ${isUp ? 'text-green-500' : isDown ? 'text-red-500' : 'text-[var(--foreground-muted)]'}`}>
                      {isUp ? <TrendingUp className="h-3 w-3" /> : isDown ? <TrendingDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
                      {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
                    </span>
                  )}
                </div>
                {ex.country && (
                  <span className="text-[10px] text-[var(--foreground-muted)]">{ex.country}</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
