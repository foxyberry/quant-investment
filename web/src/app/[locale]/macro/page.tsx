'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useMemo, type ReactNode } from 'react';
import { Card } from '@/components/ui';
import { useMacroBundle, useMacroHistory } from '@/hooks/useMarket';
import { formatPercent } from '@/lib/format';
import { Activity, CandlestickChart, DollarSign, RefreshCw, ShieldAlert, Users } from 'lucide-react';

function formatNumber(value: number | null, locale: string, maximumFractionDigits: number = 2): string {
  if (value == null || Number.isNaN(value)) return '-';
  return value.toLocaleString(locale === 'ko' ? 'ko-KR' : locale === 'zh' ? 'zh-CN' : 'en-US', {
    maximumFractionDigits,
  });
}

function formatDateTime(value: string | null, locale: string): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return new Intl.DateTimeFormat(locale === 'ko' ? 'ko-KR' : locale === 'zh' ? 'zh-CN' : 'en-US', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

export default function MacroPage() {
  const t = useTranslations('macro');
  const locale = useLocale();
  const bundleQuery = useMacroBundle();
  const historyQuery = useMacroHistory('60m');

  const regimeClass = useMemo(() => {
    const regime = bundleQuery.data?.signal.regime;
    if (regime === 'risk_on') return 'text-emerald-600 dark:text-emerald-400';
    if (regime === 'risk_off') return 'text-red-600 dark:text-red-400';
    return 'text-amber-600 dark:text-amber-400';
  }, [bundleQuery.data?.signal.regime]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">{t('title')}</h1>
          <p className="mt-1 text-[var(--foreground-muted)]">{t('subtitle')}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            void bundleQuery.refetch();
            void historyQuery.refetch();
          }}
          className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)]"
        >
          <RefreshCw className="h-4 w-4" />
          {t('refresh')}
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <p className="text-sm text-[var(--foreground-muted)]">{t('regime')}</p>
          <p className={`mt-1 text-xl font-semibold uppercase ${regimeClass}`}>
            {t(`regime_${bundleQuery.data?.signal.regime ?? 'unknown'}`)}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--foreground-muted)]">{t('macroScore')}</p>
          <p className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            {formatPercent(bundleQuery.data?.signal.macro_score ?? null)}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--foreground-muted)]">{t('lastUpdated')}</p>
          <p className="mt-1 text-xl font-semibold text-[var(--foreground)]">
            {formatDateTime(bundleQuery.data?.signal.updated_at ?? null, locale)}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--foreground-muted)]">{t('reason')}</p>
          <p className="mt-1 line-clamp-2 text-sm text-[var(--foreground)]">
            {bundleQuery.data?.signal.reason || t('noReason')}
          </p>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <MetricCard
          title="USD/KRW"
          icon={<DollarSign className="h-4 w-4" />}
          value={formatNumber(bundleQuery.data?.fx.value ?? null, locale, 2)}
          subValue={formatPercent(bundleQuery.data?.fx.change_pct ?? null)}
          ageLabel={t('ageSec', { age: bundleQuery.data?.freshness.fx_age_sec ?? '-' })}
        />
        <MetricCard
          title={t('futures')}
          icon={<CandlestickChart className="h-4 w-4" />}
          value={formatNumber(bundleQuery.data?.futures.value ?? null, locale, 2)}
          subValue={`${t('basis')}: ${formatNumber(bundleQuery.data?.futures.basis ?? null, locale, 2)}`}
          ageLabel={t('ageSec', { age: bundleQuery.data?.freshness.futures_age_sec ?? '-' })}
        />
        <MetricCard
          title={t('investorFlow')}
          icon={<Users className="h-4 w-4" />}
          value={formatNumber(bundleQuery.data?.flow.foreign_net ?? null, locale, 0)}
          subValue={`${t('institution')}: ${formatNumber(bundleQuery.data?.flow.institution_net ?? null, locale, 0)}`}
          ageLabel={t('ageSec', { age: bundleQuery.data?.freshness.flow_age_sec ?? '-' })}
        />
      </div>

      <Card title={t('historyTitle')}>
        {historyQuery.isLoading ? (
          <p className="text-sm text-[var(--foreground-muted)]">{t('loadingHistory')}</p>
        ) : historyQuery.isError ? (
          <p className="inline-flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
            <ShieldAlert className="h-4 w-4" />
            {t('historyUnavailable')}
          </p>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-[var(--foreground-muted)]">{t('historyPlaceholder')}</p>
            <div className="max-h-56 overflow-y-auto rounded-lg border border-[var(--border)]">
              <table className="min-w-full text-sm">
                <thead className="bg-[var(--background)] text-[var(--foreground-muted)]">
                  <tr>
                    <th className="px-3 py-2 text-left">{t('time')}</th>
                    <th className="px-3 py-2 text-right">USD/KRW</th>
                    <th className="px-3 py-2 text-right">{t('macroScore')}</th>
                    <th className="px-3 py-2 text-right">{t('regime')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(historyQuery.data?.points ?? []).slice(-20).reverse().map((point, idx) => (
                    <tr key={`${point.timestamp}-${idx}`} className="border-t border-[var(--border)]">
                      <td className="px-3 py-2">{formatDateTime(point.timestamp, locale)}</td>
                      <td className="px-3 py-2 text-right">{formatNumber(point.fx_value, locale, 2)}</td>
                      <td className="px-3 py-2 text-right">{formatPercent(point.macro_score)}</td>
                      <td className="px-3 py-2 text-right uppercase">{t(`regime_${point.regime}`)}</td>
                    </tr>
                  ))}
                  {(!historyQuery.data?.points || historyQuery.data.points.length === 0) && (
                    <tr>
                      <td colSpan={4} className="px-3 py-6 text-center text-[var(--foreground-muted)]">
                        {t('noHistory')}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      {bundleQuery.isError && (
        <p className="inline-flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
          <Activity className="h-4 w-4" />
          {t('bundleUnavailable')}
        </p>
      )}
    </div>
  );
}

function MetricCard({
  title,
  icon,
  value,
  subValue,
  ageLabel,
}: {
  title: string;
  icon: ReactNode;
  value: string;
  subValue: string;
  ageLabel: string;
}) {
  return (
    <Card>
      <div className="space-y-2">
        <div className="inline-flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
          {icon}
          {title}
        </div>
        <p className="text-xl font-semibold text-[var(--foreground)]">{value}</p>
        <p className="text-sm text-[var(--foreground-muted)]">{subValue}</p>
        <p className="text-xs text-[var(--foreground-muted)]">{ageLabel}</p>
      </div>
    </Card>
  );
}
