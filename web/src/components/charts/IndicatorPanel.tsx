'use client';

import { TrendingUp, TrendingDown, Minus, Activity, BarChart2, Waves, Info } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import type { TechnicalIndicators } from '@/lib/types';

interface IndicatorPanelProps {
  /** Technical indicators data */
  technicalData: TechnicalIndicators | null;
  /** Current price for signal badge derivation */
  currentPrice?: number | null;
  /** Additional CSS class */
  className?: string;
}

interface IndicatorCardProps {
  title: string;
  subtitle?: string;
  badge?: { label: string; className: string };
  icon: React.ReactNode;
  explanation?: string;
  children: React.ReactNode;
  className?: string;
}

function IndicatorCard({ title, subtitle, badge, icon, explanation, children, className = '' }: IndicatorCardProps) {
  return (
    <div className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-5 ${className}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-[var(--color-primary)]">{icon}</span>
          <div>
            <h4 className="font-semibold text-[var(--foreground)]">{title}</h4>
            {subtitle && (
              <p className="text-xs text-[var(--foreground-muted)]">{subtitle}</p>
            )}
          </div>
        </div>
        {badge && (
          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${badge.className}`}>
            {badge.label}
          </span>
        )}
      </div>
      {children}
      {explanation && (
        <div className="mt-4 rounded-lg bg-[var(--background)]/60 px-3 py-2.5 flex gap-2">
          <Info className="h-4 w-4 text-[var(--color-primary)] shrink-0 mt-0.5" />
          <p className="text-xs text-[var(--foreground-muted)] leading-relaxed">
            {explanation}
          </p>
        </div>
      )}
    </div>
  );
}

function getSignalBadge(signal: string, t: (key: string) => string): { label: string; className: string } {
  switch (signal) {
    case 'oversold':
    case 'bullish':
      return { label: t(signal === 'bullish' ? 'bullish' : 'oversold'), className: 'bg-green-500/15 text-green-500' };
    case 'overbought':
    case 'bearish':
      return { label: t(signal === 'bearish' ? 'bearish' : 'overbought'), className: 'bg-red-500/15 text-red-500' };
    case 'below':
      return { label: t('belowBand'), className: 'bg-green-500/15 text-green-500' };
    case 'above':
      return { label: t('aboveBand'), className: 'bg-red-500/15 text-red-500' };
    case 'within':
      return { label: t('inRange'), className: 'bg-blue-500/15 text-blue-500' };
    default:
      return { label: t('neutral'), className: 'bg-[var(--foreground-muted)]/15 text-[var(--foreground-muted)]' };
  }
}

function getSMASignal(smaValue: number, currentPrice: number): 'buy' | 'hold' | 'sell' {
  const diff = (currentPrice - smaValue) / smaValue;
  if (diff > 0.01) return 'buy';
  if (diff < -0.01) return 'sell';
  return 'hold';
}

function getMAOverallBadge(
  sma: NonNullable<TechnicalIndicators['sma']>,
  currentPrice: number | null | undefined,
  t: (key: string) => string,
): { label: string; className: string } {
  if (currentPrice == null) return { label: t('neutral'), className: 'bg-[var(--foreground-muted)]/15 text-[var(--foreground-muted)]' };
  const signals = [sma.sma20, sma.sma50, sma.sma200].map((v) => getSMASignal(v, currentPrice));
  const buyCount = signals.filter((s) => s === 'buy').length;
  if (buyCount === 3) return { label: t('strongBuy'), className: 'bg-green-500/15 text-green-500' };
  if (buyCount >= 2) return { label: t('buy'), className: 'bg-green-500/15 text-green-500' };
  if (buyCount === 0) return { label: t('sell'), className: 'bg-red-500/15 text-red-500' };
  return { label: t('hold'), className: 'bg-yellow-500/15 text-yellow-500' };
}

function getVolumeBadge(ratio: number, t: (key: string) => string): { label: string; className: string } {
  if (ratio >= 1.5) return { label: t('highActivity'), className: 'bg-green-500/15 text-green-500' };
  if (ratio <= 0.5) return { label: t('lowActivity'), className: 'bg-red-500/15 text-red-500' };
  return { label: t('normalActivity'), className: 'bg-[var(--foreground-muted)]/15 text-[var(--foreground-muted)]' };
}

function getBBPositionPct(
  bb: NonNullable<TechnicalIndicators['bollingerBands']>,
  currentPrice?: number | null,
): number {
  if (currentPrice != null) {
    const range = bb.upper - bb.lower;
    if (range <= 0) return 50;
    const pct = ((currentPrice - bb.lower) / range) * 100;
    return Math.max(5, Math.min(95, pct));
  }
  switch (bb.position) {
    case 'below': return 10;
    case 'above': return 90;
    default: return 50;
  }
}

/**
 * Panel displaying technical indicators matching Stitch design
 */
export default function IndicatorPanel({
  technicalData,
  currentPrice,
  className = '',
}: IndicatorPanelProps) {
  const t = useTranslations('indicators');

  if (!technicalData) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-center py-8">
          <p className="text-[var(--foreground-muted)]">
            No technical data available
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className={`grid grid-cols-1 lg:grid-cols-2 gap-4 ${className}`}>
      {/* RSI Indicator */}
      {technicalData.rsi && (
        <IndicatorCard
          title="RSI (14)"
          subtitle={t('rsiSubtitle')}
          badge={getSignalBadge(technicalData.rsi.signal, t)}
          icon={<Activity className="h-5 w-5" />}
          explanation={t('rsiExplain')}
        >
          <div className="space-y-3">
            <p className="text-3xl font-bold font-mono text-[var(--foreground)]">
              {technicalData.rsi.value.toFixed(2)}
            </p>
            {/* Color-segmented gauge */}
            <div className="relative">
              <div className="flex h-3 rounded-full overflow-hidden">
                <div className="w-[30%] bg-red-500/40" />
                <div className="w-[40%] bg-blue-500/30" />
                <div className="w-[30%] bg-blue-500/40" />
              </div>
              {/* Position marker */}
              <div
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
                style={{ left: `${Math.min(100, technicalData.rsi.value)}%` }}
              >
                <div className="w-1 h-5 bg-[var(--foreground)] rounded-full shadow" />
              </div>
            </div>
            <div className="flex justify-between text-xs text-[var(--foreground-muted)]">
              <span>{t('rsiScaleOversold')}</span>
              <span>{t('rsiScaleMid')}</span>
              <span>{t('rsiScaleOverbought')}</span>
            </div>
          </div>
        </IndicatorCard>
      )}

      {/* MACD Indicator */}
      {technicalData.macd && (
        <IndicatorCard
          title="MACD (12, 26, 9)"
          subtitle={t('macdSubtitle')}
          badge={getSignalBadge(technicalData.macd.trend, t)}
          icon={<BarChart2 className="h-5 w-5" />}
          explanation={t('macdExplain')}
        >
          <div className="space-y-3">
            {/* Momentum summary — the key takeaway */}
            <div className={`flex items-center gap-2 rounded-lg px-3 py-2 ${
              technicalData.macd.histogram >= 0
                ? 'bg-green-500/10'
                : 'bg-red-500/10'
            }`}>
              {technicalData.macd.histogram >= 0
                ? <TrendingUp className="h-5 w-5 text-green-500" />
                : <TrendingDown className="h-5 w-5 text-red-500" />}
              <span className={`text-sm font-semibold ${
                technicalData.macd.histogram >= 0 ? 'text-green-500' : 'text-red-500'
              }`}>
                {technicalData.macd.histogram >= 0
                  ? t('macdMomentumUp')
                  : t('macdMomentumDown')}
              </span>
            </div>

            {/* MACD vs Signal lines */}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg bg-[var(--background)]/60 border border-[var(--border)]/50 px-3 py-2">
                <span className="text-xs text-[var(--foreground-muted)]">{t('macdLine')}</span>
                <p className="text-lg font-bold font-mono text-[var(--foreground)]">
                  {technicalData.macd.macd.toFixed(2)}
                </p>
              </div>
              <div className="rounded-lg bg-[var(--background)]/60 border border-[var(--border)]/50 px-3 py-2">
                <span className="text-xs text-[var(--foreground-muted)]">{t('signalLine')}</span>
                <p className="text-lg font-bold font-mono text-[var(--foreground)]">
                  {technicalData.macd.signal.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Histogram bar */}
            <div className="rounded-lg bg-[var(--background)]/60 px-3 py-2">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-[var(--foreground-muted)]">{t('histogram')}</span>
                <span className={`text-sm font-bold font-mono ${
                  technicalData.macd.histogram >= 0 ? 'text-green-500' : 'text-red-500'
                }`}>
                  {technicalData.macd.histogram >= 0 ? '+' : ''}{technicalData.macd.histogram.toFixed(2)}
                </span>
              </div>
              {/* Visual bar centered at zero */}
              <div className="relative h-3 rounded-full bg-[var(--border)]/30 overflow-hidden">
                <div className="absolute top-0 left-1/2 h-full w-px bg-[var(--foreground-muted)]/40" />
                {technicalData.macd.histogram >= 0 ? (
                  <div
                    className="absolute top-0 left-1/2 h-full rounded-r-full bg-green-500/60"
                    style={{ width: `${Math.min(50, Math.abs(technicalData.macd.histogram) / (Math.abs(technicalData.macd.macd) + Math.abs(technicalData.macd.signal) || 1) * 50)}%` }}
                  />
                ) : (
                  <div
                    className="absolute top-0 right-1/2 h-full rounded-l-full bg-red-500/60"
                    style={{ width: `${Math.min(50, Math.abs(technicalData.macd.histogram) / (Math.abs(technicalData.macd.macd) + Math.abs(technicalData.macd.signal) || 1) * 50)}%` }}
                  />
                )}
              </div>
            </div>
          </div>
        </IndicatorCard>
      )}

      {/* Bollinger Bands */}
      {technicalData.bollingerBands && (() => {
        const positionPct = getBBPositionPct(technicalData.bollingerBands, currentPrice);
        return (
          <IndicatorCard
            title="Bollinger Bands"
            subtitle={t('bbSubtitle')}
            badge={getSignalBadge(technicalData.bollingerBands.position, t)}
            icon={<Waves className="h-5 w-5" />}
            explanation={t('bollingerExplain')}
          >
            <div className="space-y-4">
              {/* Horizontal band diagram */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-[var(--foreground-muted)]">
                  <span className="text-green-500 font-medium">{t('bbZoneLow')}</span>
                  <span className="uppercase tracking-wider text-[10px]">{t('bbZoneNormal')}</span>
                  <span className="text-red-500 font-medium">{t('bbZoneHigh')}</span>
                </div>
                <div className="relative">
                  <div className="h-3 rounded-full overflow-hidden bg-gradient-to-r from-green-500/30 via-blue-500/20 to-red-500/30" />
                  {/* Dashed boundary lines */}
                  <div className="absolute top-0 left-[25%] h-full border-l border-dashed border-[var(--foreground-muted)]/30" />
                  <div className="absolute top-0 left-[75%] h-full border-l border-dashed border-[var(--foreground-muted)]/30" />
                  {/* Current position dot */}
                  <div
                    className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
                    style={{ left: `${positionPct}%` }}
                  >
                    <div className="h-4 w-4 rounded-full bg-blue-500 border-2 border-white dark:border-gray-800 shadow-lg" />
                  </div>
                </div>
                <div className="text-center">
                  <span className="text-xs text-blue-500 font-medium">{t('bbCurrentPosition')}</span>
                </div>
              </div>
            </div>
          </IndicatorCard>
        );
      })()}

      {/* Moving Averages */}
      {technicalData.sma && (
        <IndicatorCard
          title="Moving Averages"
          subtitle={t('maSubtitle')}
          badge={getMAOverallBadge(technicalData.sma, currentPrice, t)}
          icon={<TrendingUp className="h-5 w-5" />}
          explanation={t('maExplain')}
        >
          <div className="grid grid-cols-2 gap-2">
            {([
              { label: 'SMA 20', value: technicalData.sma.sma20 },
              { label: 'SMA 50', value: technicalData.sma.sma50 },
              { label: 'SMA 200', value: technicalData.sma.sma200 },
            ] as const).map((item) => {
              const signal = currentPrice != null ? getSMASignal(item.value, currentPrice) : null;
              return (
                <div
                  key={item.label}
                  className="rounded-lg bg-[var(--background)]/60 border border-[var(--border)]/50 px-3 py-2.5"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-[var(--foreground-muted)]">{item.label}</span>
                    {signal && (
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                          signal === 'buy'
                            ? 'bg-green-500/15 text-green-500'
                            : signal === 'sell'
                            ? 'bg-red-500/15 text-red-500'
                            : 'bg-yellow-500/15 text-yellow-500'
                        }`}
                      >
                        {t(signal)}
                      </span>
                    )}
                  </div>
                  <p className="text-lg font-bold font-mono text-[var(--foreground)]">
                    {item.value.toFixed(2)}
                  </p>
                </div>
              );
            })}
          </div>
        </IndicatorCard>
      )}

      {/* Volume Analysis — full width */}
      {technicalData.volume && (
        <IndicatorCard
          title="Volume Analysis"
          subtitle={t('volumeSubtitle')}
          badge={getVolumeBadge(technicalData.volume.ratio, t)}
          icon={<BarChart2 className="h-5 w-5" />}
          explanation={t('volumeExplain')}
          className="lg:col-span-2"
        >
          <div className="flex flex-col md:flex-row md:items-end gap-4">
            {/* Current volume */}
            <div className="shrink-0">
              <span className="text-xs text-[var(--foreground-muted)]">{t('currentVol')}</span>
              <div className="flex items-baseline gap-2">
                <p className="text-3xl font-bold font-mono text-[var(--foreground)]">
                  {formatVolume(technicalData.volume.current)}
                </p>
                <span
                  className={`text-sm font-semibold ${
                    technicalData.volume.ratio >= 1
                      ? 'text-green-500'
                      : 'text-red-500'
                  }`}
                >
                  {technicalData.volume.ratio >= 1 ? '↗' : '↘'}
                  {((technicalData.volume.ratio - 1) * 100).toFixed(0)}%
                </span>
              </div>
              <span className="text-xs text-[var(--foreground-muted)]">
                vs {t('avgVol')} {formatVolume(technicalData.volume.average)}
              </span>
            </div>
            {/* Volume bar */}
            <div className="flex-1">
              <div className="relative h-8 rounded-lg bg-[var(--background)]/60 overflow-hidden">
                {/* Average marker */}
                <div
                  className="absolute top-0 h-full border-l-2 border-dashed border-[var(--foreground-muted)]/40 z-10"
                  style={{ left: `${Math.min(100, (1 / Math.max(technicalData.volume.ratio, 0.01)) * 60)}%` }}
                />
                {/* Current volume bar */}
                <div
                  className={`h-full rounded-lg transition-all ${
                    technicalData.volume.ratio >= 1.5
                      ? 'bg-green-500/30'
                      : technicalData.volume.ratio >= 1
                      ? 'bg-blue-500/30'
                      : 'bg-red-500/30'
                  }`}
                  style={{ width: `${Math.min(100, technicalData.volume.ratio * 60)}%` }}
                />
              </div>
              <div className="flex justify-between mt-1 text-[10px] text-[var(--foreground-muted)]">
                <span>{t('avgVol')}</span>
                <span>{t('currentVol')}</span>
              </div>
            </div>
          </div>
        </IndicatorCard>
      )}
    </div>
  );
}

function formatVolume(volume: number): string {
  if (volume >= 1_000_000_000) {
    return `${(volume / 1_000_000_000).toFixed(1)}B`;
  }
  if (volume >= 1_000_000) {
    return `${(volume / 1_000_000).toFixed(1)}M`;
  }
  if (volume >= 1_000) {
    return `${(volume / 1_000).toFixed(1)}K`;
  }
  return volume.toFixed(0);
}
