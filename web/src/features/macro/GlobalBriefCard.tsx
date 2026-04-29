'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import { useGlobalBrief } from '@/hooks/useMarket';
import { Globe, AlertTriangle, Shield, Flame, TrendingUp, Cloud } from 'lucide-react';

const DOMAIN_ICON: Record<string, typeof Globe> = {
  geopolitics: Shield,
  finance: TrendingUp,
  energy: Flame,
  climate: Cloud,
  security: AlertTriangle,
};

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'text-red-500',
  high: 'text-orange-500',
  medium: 'text-yellow-500',
  low: 'text-[var(--foreground-muted)]',
};

export default function GlobalBriefCard() {
  const t = useTranslations('macro');
  const { data, isLoading } = useGlobalBrief();

  if (isLoading) {
    return (
      <Card className="animate-pulse p-4">
        <div className="h-6 w-40 rounded bg-[var(--background-secondary)]" />
        <div className="mt-3 space-y-2">
          {[1, 2, 3].map((i) => (
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
          <Globe className="h-5 w-5" />
          <span>{t('worldmonitorUnavailable')}</span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <Globe className="h-5 w-5 text-[var(--accent)]" />
          {t('globalBrief')}
        </h3>
        {data.generated_at && (
          <span className="text-xs text-[var(--foreground-muted)]">
            {new Date(data.generated_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      <div className="mt-3 space-y-3">
        {data.items.length === 0 && (
          <p className="text-sm text-[var(--foreground-muted)]">{t('noBriefItems')}</p>
        )}
        {data.items.map((item, i) => {
          const Icon = DOMAIN_ICON[item.domain ?? ''] ?? Globe;
          const sevClass = SEVERITY_COLOR[item.severity ?? 'low'] ?? '';
          return (
            <div key={i} className="rounded-lg border border-[var(--border)] p-3">
              <div className="flex items-start gap-2">
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${sevClass}`} />
                <div className="min-w-0">
                  <p className="text-sm font-medium">{item.headline ?? '-'}</p>
                  {item.summary && (
                    <p className="mt-1 text-xs text-[var(--foreground-muted)] line-clamp-2">{item.summary}</p>
                  )}
                  <div className="mt-1 flex gap-2 text-xs text-[var(--foreground-muted)]">
                    {item.domain && <span className="capitalize">{item.domain}</span>}
                    {item.region && <span>{item.region}</span>}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
