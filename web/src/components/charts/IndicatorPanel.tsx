'use client';

import { TrendingUp, TrendingDown, Minus, Activity, BarChart2, Waves, Info } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui';
import type { TechnicalIndicators } from '@/lib/types';

interface IndicatorPanelProps {
  /** Technical indicators data */
  technicalData: TechnicalIndicators | null;
  /** Additional CSS class */
  className?: string;
}

interface IndicatorCardProps {
  title: string;
  icon: React.ReactNode;
  explanation?: string;
  children: React.ReactNode;
}

function IndicatorCard({ title, icon, explanation, children }: IndicatorCardProps) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[var(--color-primary)]">{icon}</span>
        <h4 className="font-medium text-[var(--foreground)]">{title}</h4>
      </div>
      {children}
      {explanation && (
        <div className="mt-3 rounded-lg bg-[var(--background)]/60 px-3 py-2.5 flex gap-2">
          <Info className="h-4 w-4 text-[var(--color-primary)] shrink-0 mt-0.5" />
          <p className="text-xs text-[var(--foreground-muted)] leading-relaxed">
            {explanation}
          </p>
        </div>
      )}
    </div>
  );
}

function getSignalColor(signal: string): string {
  switch (signal) {
    case 'oversold':
    case 'bullish':
    case 'below':
      return 'text-green-600 dark:text-green-400';
    case 'overbought':
    case 'bearish':
    case 'above':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-[var(--foreground-muted)]';
  }
}

function getSignalIcon(signal: string) {
  switch (signal) {
    case 'oversold':
    case 'bullish':
    case 'below':
      return <TrendingUp className="h-4 w-4" />;
    case 'overbought':
    case 'bearish':
    case 'above':
      return <TrendingDown className="h-4 w-4" />;
    default:
      return <Minus className="h-4 w-4" />;
  }
}

function getSignalLabel(signal: string, t: (key: string) => string): string {
  switch (signal) {
    case 'oversold':
      return t('oversold');
    case 'overbought':
      return t('overbought');
    case 'bullish':
      return t('bullish');
    case 'bearish':
      return t('bearish');
    case 'above':
      return t('aboveBand');
    case 'below':
      return t('belowBand');
    case 'within':
      return t('withinBand');
    default:
      return t('neutral');
  }
}

/**
 * Panel displaying technical indicators in a card-based layout
 */
export default function IndicatorPanel({
  technicalData,
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
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 ${className}`}>
      {/* RSI Indicator */}
      {technicalData.rsi && (
        <IndicatorCard
          title="RSI (14)"
          icon={<Activity className="h-5 w-5" />}
          explanation={t('rsiExplain')}
        >
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold text-[var(--foreground)]">
                {technicalData.rsi.value.toFixed(2)}
              </span>
              <div
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${getSignalColor(
                  technicalData.rsi.signal
                )} bg-[var(--background)]`}
              >
                {getSignalIcon(technicalData.rsi.signal)}
                {getSignalLabel(technicalData.rsi.signal, t)}
              </div>
            </div>
            {/* RSI gauge */}
            <div className="relative h-2 rounded-full bg-[var(--border)] overflow-hidden">
              <div
                className="absolute h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(100, technicalData.rsi.value)}%`,
                  backgroundColor:
                    technicalData.rsi.value < 30
                      ? '#22c55e'
                      : technicalData.rsi.value > 70
                      ? '#ef4444'
                      : '#60a5fa',
                }}
              />
            </div>
            <div className="flex justify-between text-xs text-[var(--foreground-muted)]">
              <span>0</span>
              <span>30</span>
              <span>70</span>
              <span>100</span>
            </div>
          </div>
        </IndicatorCard>
      )}

      {/* MACD Indicator */}
      {technicalData.macd && (
        <IndicatorCard
          title="MACD"
          icon={<BarChart2 className="h-5 w-5" />}
          explanation={t('macdExplain')}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs text-[var(--foreground-muted)]">MACD</span>
                <p className="text-lg font-semibold text-[var(--foreground)]">
                  {technicalData.macd.macd.toFixed(4)}
                </p>
              </div>
              <div
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${getSignalColor(
                  technicalData.macd.trend
                )} bg-[var(--background)]`}
              >
                {getSignalIcon(technicalData.macd.trend)}
                {getSignalLabel(technicalData.macd.trend, t)}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-[var(--foreground-muted)]">Signal</span>
                <p className="font-medium text-[var(--foreground)]">
                  {technicalData.macd.signal.toFixed(4)}
                </p>
              </div>
              <div>
                <span className="text-[var(--foreground-muted)]">Histogram</span>
                <p
                  className={`font-medium ${
                    technicalData.macd.histogram >= 0
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {technicalData.macd.histogram >= 0 ? '+' : ''}
                  {technicalData.macd.histogram.toFixed(4)}
                </p>
              </div>
            </div>
          </div>
        </IndicatorCard>
      )}

      {/* Bollinger Bands */}
      {technicalData.bollingerBands && (
        <IndicatorCard
          title="Bollinger Bands"
          icon={<Waves className="h-5 w-5" />}
          explanation={t('bollingerExplain')}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--foreground-muted)]">Position</span>
              <div
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${getSignalColor(
                  technicalData.bollingerBands.position
                )} bg-[var(--background)]`}
              >
                {getSignalIcon(technicalData.bollingerBands.position)}
                {getSignalLabel(technicalData.bollingerBands.position, t)}
              </div>
            </div>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--foreground-muted)]">Upper Band</span>
                <span className="font-medium text-[var(--foreground)]">
                  ${technicalData.bollingerBands.upper.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--foreground-muted)]">Middle Band</span>
                <span className="font-medium text-[var(--foreground)]">
                  ${technicalData.bollingerBands.middle.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--foreground-muted)]">Lower Band</span>
                <span className="font-medium text-[var(--foreground)]">
                  ${technicalData.bollingerBands.lower.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </IndicatorCard>
      )}

      {/* Moving Averages */}
      {technicalData.sma && (
        <IndicatorCard
          title="Moving Averages"
          icon={<TrendingUp className="h-5 w-5" />}
          explanation={t('maExplain')}
        >
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--foreground-muted)]">SMA 20</span>
              <span className="font-medium text-[var(--foreground)]">
                ${technicalData.sma.sma20.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--foreground-muted)]">SMA 50</span>
              <span className="font-medium text-[var(--foreground)]">
                ${technicalData.sma.sma50.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--foreground-muted)]">SMA 200</span>
              <span className="font-medium text-[var(--foreground)]">
                ${technicalData.sma.sma200.toFixed(2)}
              </span>
            </div>
          </div>
        </IndicatorCard>
      )}

      {/* Volume Analysis */}
      {technicalData.volume && (
        <IndicatorCard
          title="Volume Analysis"
          icon={<BarChart2 className="h-5 w-5" />}
          explanation={t('volumeExplain')}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--foreground-muted)]">Volume Ratio</span>
              <span
                className={`text-lg font-semibold ${
                  technicalData.volume.ratio >= 1.5
                    ? 'text-green-600 dark:text-green-400'
                    : technicalData.volume.ratio <= 0.5
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-[var(--foreground)]'
                }`}
              >
                {technicalData.volume.ratio.toFixed(2)}x
              </span>
            </div>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--foreground-muted)]">Current Volume</span>
                <span className="font-medium text-[var(--foreground)]">
                  {formatVolume(technicalData.volume.current)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--foreground-muted)]">Average Volume</span>
                <span className="font-medium text-[var(--foreground)]">
                  {formatVolume(technicalData.volume.average)}
                </span>
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
    return `${(volume / 1_000_000_000).toFixed(2)}B`;
  }
  if (volume >= 1_000_000) {
    return `${(volume / 1_000_000).toFixed(2)}M`;
  }
  if (volume >= 1_000) {
    return `${(volume / 1_000).toFixed(2)}K`;
  }
  return volume.toFixed(0);
}
