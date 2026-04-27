'use client';

import { useTranslations } from 'next-intl';
import type { TickerAnalysis } from '@/lib/types';

interface FundamentalCardProps {
  fundamental: NonNullable<TickerAnalysis['fundamental']>;
  className?: string;
}

function formatValue(value: number | null | undefined, type: 'ratio' | 'percent' | 'currency' | 'number'): string {
  if (value == null) return 'N/A';
  switch (type) {
    case 'ratio':
      return value.toFixed(2);
    case 'percent':
      // API returns percent values already scaled (e.g., 27.03 means 27.03%)
      return `${value.toFixed(1)}%`;
    case 'currency':
      if (Math.abs(value) >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
      if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
      if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
      return `$${value.toFixed(2)}`;
    case 'number':
      return value.toFixed(2);
    default:
      return String(value);
  }
}

export default function FundamentalCard({ fundamental, className = '' }: FundamentalCardProps) {
  const t = useTranslations('fundamentals');

  const metrics: { label: string; value: string; highlight?: boolean }[] = [
    { label: t('peRatio'), value: formatValue(fundamental.pe_ratio, 'ratio') },
    { label: t('forwardPE'), value: formatValue(fundamental.forward_pe, 'ratio') },
    { label: t('pbRatio'), value: formatValue(fundamental.pb_ratio, 'ratio') },
    { label: t('psRatio'), value: formatValue(fundamental.ps_ratio, 'ratio') },
    { label: t('pegRatio'), value: formatValue(fundamental.peg_ratio, 'ratio') },
    { label: t('marketCap'), value: formatValue(fundamental.market_cap, 'currency'), highlight: true },
    { label: t('revenue'), value: formatValue(fundamental.revenue, 'currency') },
    { label: t('revenueGrowth'), value: formatValue(fundamental.revenue_growth, 'percent') },
    { label: t('profitMargin'), value: formatValue(fundamental.profit_margin, 'percent') },
    { label: t('roe'), value: formatValue(fundamental.roe, 'percent') },
    { label: t('roa'), value: formatValue(fundamental.roa, 'percent') },
    { label: t('debtToEquity'), value: formatValue(fundamental.debt_to_equity, 'ratio') },
    { label: t('currentRatio'), value: formatValue(fundamental.current_ratio, 'ratio') },
    { label: t('eps'), value: formatValue(fundamental.eps, 'number') },
  ];

  return (
    <div className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-5 ${className}`}>
      <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">{t('title')}</h3>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        {metrics.map((m) => (
          <div key={m.label} className="flex items-center justify-between">
            <span className="text-xs text-[var(--foreground-muted)]">{m.label}</span>
            <span className={`text-sm font-mono font-semibold ${
              m.highlight ? 'text-[var(--color-primary)]' : 'text-[var(--foreground)]'
            }`}>
              {m.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
