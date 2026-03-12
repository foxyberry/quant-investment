'use client';

import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { Card } from '@/components/ui';
import { useMacroBundle } from '@/hooks/useMarket';
import { formatPercent } from '@/lib/format';
import { Activity, ArrowRight, CandlestickChart, DollarSign, Users } from 'lucide-react';

function formatNumber(value: number | null, locale: string, maximumFractionDigits: number = 2): string {
  if (value == null || Number.isNaN(value)) return '-';
  return value.toLocaleString(locale === 'ko' ? 'ko-KR' : locale === 'zh' ? 'zh-CN' : 'en-US', {
    maximumFractionDigits,
  });
}

export default function MacroFlowCard() {
  const t = useTranslations('dashboard');
  const locale = useLocale();
  const { data, isLoading, isError } = useMacroBundle();

  if (isLoading) {
    return (
      <Card title={t('macroFlow')}>
        <div className="space-y-3 animate-pulse">
          <div className="h-8 rounded bg-[var(--border)]" />
          <div className="h-8 rounded bg-[var(--border)]" />
          <div className="h-8 rounded bg-[var(--border)]" />
        </div>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card title={t('macroFlow')}>
        <p className="text-sm text-[var(--foreground-muted)]">{t('macroUnavailable')}</p>
        <Link
          href="/macro"
          className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[var(--color-primary)] hover:opacity-80"
        >
          {t('viewMacroDetails')}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </Card>
    );
  }

  const regime = data.signal?.regime;
  const regimeClass =
    regime === 'risk_on'
      ? 'text-emerald-600 dark:text-emerald-400'
      : regime === 'risk_off'
      ? 'text-red-600 dark:text-red-400'
      : 'text-amber-600 dark:text-amber-400';

  return (
    <Card title={t('macroFlow')}>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-[var(--foreground-muted)]">{t('macroRegime')}</span>
          <span className={`text-sm font-semibold uppercase ${regimeClass}`}>
            {t(`macroRegime_${regime ?? 'unknown'}`)}
          </span>
        </div>

        <div className="grid gap-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1 text-[var(--foreground-muted)]">
              <DollarSign className="h-4 w-4" /> USD/KRW
            </span>
            <span className="font-medium text-[var(--foreground)]">{formatNumber(data.fx?.value ?? null, locale, 2)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1 text-[var(--foreground-muted)]">
              <CandlestickChart className="h-4 w-4" /> {t('futures')}
            </span>
            <span className="font-medium text-[var(--foreground)]">{formatNumber(data.futures?.basis ?? null, locale, 2)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1 text-[var(--foreground-muted)]">
              <Users className="h-4 w-4" /> {t('investorFlow')}
            </span>
            <span className="font-medium text-[var(--foreground)]">{formatNumber(data.flow?.foreign_net ?? null, locale, 0)}</span>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-[var(--border)] pt-2 text-xs text-[var(--foreground-muted)]">
          <span className="inline-flex items-center gap-1">
            <Activity className="h-3.5 w-3.5" />
            {t('macroScore')}: {formatPercent(data.signal?.macro_score ?? null)}
          </span>
          <Link href="/macro" className="inline-flex items-center gap-1 font-medium text-[var(--color-primary)] hover:opacity-80">
            {t('viewDetails')}
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </Card>
  );
}
