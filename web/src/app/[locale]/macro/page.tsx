'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useMemo, useState, type ReactNode } from 'react';
import { Card } from '@/components/ui';
import { useMacroBundle, useMacroHistory, useOhlcv } from '@/hooks/useMarket';
import CandleChart from '@/components/charts/CandleChart';
import { formatPercent } from '@/lib/format';
import {
  Activity,
  AlertTriangle,
  CandlestickChart,
  CheckCircle,
  DollarSign,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea,
  Legend,
} from 'recharts';
import type { MacroEntrySignal, MacroRegime } from '@/lib/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatNumber(value: number | null, locale: string, maximumFractionDigits = 2): string {
  if (value == null || Number.isNaN(value)) return '-';
  return value.toLocaleString(locale === 'ko' ? 'ko-KR' : locale === 'zh' ? 'zh-CN' : 'en-US', {
    maximumFractionDigits,
  });
}

function formatFlowBillion(value: number | null, locale: string): string {
  if (value == null || Number.isNaN(value)) return '-';
  const billion = value / 100_000_000; // 원 → 억원
  const prefix = billion > 0 ? '+' : '';
  return prefix + formatNumber(Math.round(billion), locale, 0);
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

function formatShortTime(value: string | null, locale: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(locale === 'ko' ? 'ko-KR' : locale === 'zh' ? 'zh-CN' : 'en-US', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/** Parse reason string "neutral: fx=0.12 (decay=0.89), futures=-0.30 (decay=0.50), flow=0.00 (decay=0.00)" */
function parseSignalContributions(reason: string | null): { fx: number | null; futures: number | null; flow: number | null } {
  if (!reason) return { fx: null, futures: null, flow: null };
  const extract = (key: string) => {
    const match = reason.match(new RegExp(`${key}=([\\-\\d.]+)`));
    if (!match) return null;
    const val = parseFloat(match[1]);
    return Number.isNaN(val) ? null : val;
  };
  return { fx: extract('fx'), futures: extract('futures'), flow: extract('flow') };
}

const STALE_THRESHOLD_SEC = 600; // half-life

const REGIME_COLORS: Record<MacroRegime, string> = {
  risk_on: 'rgba(16, 185, 129, 0.08)',
  risk_off: 'rgba(239, 68, 68, 0.08)',
  neutral: 'rgba(245, 158, 11, 0.04)',
  unknown: 'rgba(156, 163, 175, 0.04)',
};

type WindowOption = '60m' | '6h' | '1d';

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function MacroPage() {
  const t = useTranslations('macro');
  const locale = useLocale();
  const bundleQuery = useMacroBundle();
  const [historyWindow, setHistoryWindow] = useState<WindowOption>('60m');
  const historyQuery = useMacroHistory(historyWindow);
  const futuresTicker = bundleQuery.data?.futures.symbol || '069500.KS';
  const futuresOhlcv = useOhlcv(futuresTicker, 30);

  const regime = bundleQuery.data?.signal.regime ?? 'unknown';
  const interpretation = bundleQuery.data?.interpretation;

  const regimeStyle = useMemo(() => {
    if (regime === 'risk_on') return { text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800' };
    if (regime === 'risk_off') return { text: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800' };
    return { text: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800' };
  }, [regime]);

  const contributions = useMemo(
    () => parseSignalContributions(bundleQuery.data?.signal.reason ?? null),
    [bundleQuery.data?.signal.reason],
  );

  // Compute regime segments for chart background
  const regimeSegments = useMemo(() => {
    const points = historyQuery.data?.points ?? [];
    if (points.length < 2) return [];
    const segments: { x1: string; x2: string; regime: MacroRegime }[] = [];
    let start = 0;
    for (let i = 1; i < points.length; i++) {
      if (points[i].regime !== points[start].regime) {
        segments.push({
          x1: points[start].timestamp,
          x2: points[i - 1].timestamp,
          regime: points[start].regime,
        });
        start = i;
      }
    }
    // Always close the last segment
    segments.push({
      x1: points[start].timestamp,
      x2: points[points.length - 1].timestamp,
      regime: points[start].regime,
    });
    return segments;
  }, [historyQuery.data?.points]);

  return (
    <div className="space-y-6">
      {/* Header */}
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
            void futuresOhlcv.refetch();
          }}
          className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)]"
        >
          <RefreshCw className="h-4 w-4" />
          {t('refresh')}
        </button>
      </div>

      {/* Market Entry Assessment */}
      {interpretation && <MarketEntryAssessment entrySignal={interpretation.entry_signal} fxInterp={interpretation.fx_interpretation} futuresInterp={interpretation.futures_interpretation} flowInterp={interpretation.flow_interpretation} t={t} />}

      {/* Regime Insight Banner */}
      <div className={`rounded-xl border p-4 ${regimeStyle.bg}`}>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className={`text-3xl font-bold uppercase ${regimeStyle.text}`}>
              {t(`regime_${regime}`)}
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-[var(--foreground)]">
                {formatPercent(bundleQuery.data?.signal.macro_score ?? null)}
              </span>
              <span className="text-xs text-[var(--foreground-muted)]">
                {formatDateTime(bundleQuery.data?.signal.updated_at ?? null, locale)}
              </span>
            </div>
          </div>
          <p className="text-sm text-[var(--foreground)]">
            {t(`insight${regime === 'risk_on' ? 'RiskOn' : regime === 'risk_off' ? 'RiskOff' : regime === 'neutral' ? 'Neutral' : 'Unknown'}`)}
          </p>
        </div>

        {/* Signal Contribution Bars */}
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <SignalBar label={t('fxSignal')} value={contributions.fx} nullLabel={t('flowUnavailable')} t={t} />
          <SignalBar label={t('futuresSignal')} value={contributions.futures} nullLabel={t('flowUnavailable')} t={t} />
          <SignalBar label={t('flowSignal')} value={contributions.flow} nullLabel={t('flowUnavailable')} t={t} />
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid gap-4 lg:grid-cols-3">
        <MetricCard
          title="USD/KRW"
          icon={<DollarSign className="h-4 w-4" />}
          value={formatNumber(bundleQuery.data?.fx.value ?? null, locale, 2)}
          unit={t('fxUnit')}
          source={t('fxSource')}
          items={[
            { label: t('changePct'), value: formatPercent(bundleQuery.data?.fx.change_pct ?? null) },
          ]}
          ageSec={bundleQuery.data?.freshness.fx_age_sec ?? null}
          ageLabel={t('ageSec', { age: bundleQuery.data?.freshness.fx_age_sec ?? '-' })}
          staleLabel={t('staleWarning')}
          interpretationText={interpretation ? t(`interp_fx_${interpretation.fx_interpretation}`) : undefined}
        />
        <MetricCard
          title={t('futures')}
          icon={<CandlestickChart className="h-4 w-4" />}
          value={formatNumber(bundleQuery.data?.futures.value ?? null, locale, 0)}
          unit={t('futuresUnit')}
          source={t('futuresSource')}
          items={[
            { label: t('basis'), value: bundleQuery.data?.futures.basis != null ? `${bundleQuery.data.futures.basis > 0 ? '+' : ''}${formatNumber(bundleQuery.data.futures.basis, locale, 3)}%` : '-' },
            { label: t('changePct'), value: formatPercent(bundleQuery.data?.futures.change_pct ?? null) },
          ]}
          ageSec={bundleQuery.data?.freshness.futures_age_sec ?? null}
          ageLabel={t('ageSec', { age: bundleQuery.data?.freshness.futures_age_sec ?? '-' })}
          staleLabel={t('staleWarning')}
          interpretationText={interpretation ? t(`interp_futures_${interpretation.futures_interpretation}`) : undefined}
        />
        <MetricCard
          title={t('investorFlow')}
          icon={<Users className="h-4 w-4" />}
          value={
            bundleQuery.data?.flow.foreign_net != null
              ? formatFlowBillion(bundleQuery.data.flow.foreign_net, locale)
              : t('flowUnavailable')
          }
          unit={t('flowUnit')}
          source={t('flowSource')}
          items={[
            { label: t('institution'), value: formatFlowBillion(bundleQuery.data?.flow.institution_net ?? null, locale) },
            { label: t('individual'), value: formatFlowBillion(bundleQuery.data?.flow.individual_net ?? null, locale) },
          ]}
          ageSec={bundleQuery.data?.freshness.flow_age_sec ?? null}
          ageLabel={t('ageSec', { age: bundleQuery.data?.freshness.flow_age_sec ?? '-' })}
          staleLabel={t('staleWarning')}
          interpretationText={interpretation ? t(`interp_flow_${interpretation.flow_interpretation}`) : undefined}
        />
      </div>

      {/* Timeline Chart */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <div className="flex flex-col gap-1">
            <h3 className="text-base font-semibold text-[var(--foreground)]">{t('historyChart')}</h3>
            <div className="flex items-center gap-3 text-[10px] text-[var(--foreground-muted)]">
              <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />{t('regimeRiskOn')}</span>
              <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-red-400" />{t('regimeRiskOff')}</span>
              <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-amber-400" />{t('regimeNeutral')}</span>
            </div>
          </div>
          <div className="inline-flex shrink-0 rounded-lg border border-[var(--border)] overflow-hidden">
            {(['60m', '6h', '1d'] as WindowOption[]).map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => setHistoryWindow(w)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  historyWindow === w
                    ? 'bg-[var(--accent)] text-white'
                    : 'bg-[var(--background-secondary)] text-[var(--foreground-muted)] hover:bg-[var(--background)]'
                }`}
              >
                {t(`window${w === '60m' ? '1h' : w === '6h' ? '6h' : '1d'}`)}
              </button>
            ))}
          </div>
        </div>

        {historyQuery.isLoading ? (
          <div className="flex h-72 items-center justify-center">
            <p className="text-sm text-[var(--foreground-muted)]">{t('loadingHistory')}</p>
          </div>
        ) : historyQuery.isError ? (
          <div className="flex h-72 items-center justify-center">
            <p className="inline-flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
              <ShieldAlert className="h-4 w-4" />
              {t('historyUnavailable')}
            </p>
          </div>
        ) : (!historyQuery.data?.points || historyQuery.data.points.length === 0) ? (
          <div className="flex h-72 flex-col items-center justify-center gap-2">
            <p className="text-sm text-[var(--foreground-muted)]">{t('noHistory')}</p>
            {historyWindow !== '60m' && (
              <p className="text-xs text-[var(--foreground-muted)]">{t('historyAccumulating')}</p>
            )}
          </div>
        ) : (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={historyQuery.data.points} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                {regimeSegments.map((seg, i) => (
                  <ReferenceArea
                    key={`regime-${i}`}
                    x1={seg.x1}
                    x2={seg.x2}
                    fill={REGIME_COLORS[seg.regime]}
                    fillOpacity={1}
                  />
                ))}
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(v: string) => formatShortTime(v, locale)}
                  tick={{ fontSize: 11, fill: 'var(--foreground-muted)' }}
                  stroke="var(--border)"
                />
                <YAxis
                  yAxisId="fx"
                  orientation="left"
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: 'var(--foreground-muted)' }}
                  stroke="var(--border)"
                  tickFormatter={(v: number) => v.toFixed(0)}
                  width={60}
                />
                <YAxis
                  yAxisId="score"
                  orientation="right"
                  domain={[-1, 1]}
                  tick={{ fontSize: 11, fill: 'var(--foreground-muted)' }}
                  stroke="var(--border)"
                  tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                  width={50}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--background-secondary)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    fontSize: 12,
                  }}
                  labelFormatter={(v) => formatDateTime(String(v), locale)}
                  formatter={(value, name) => {
                    if (value == null || value === '') return ['-', name];
                    const v = Number(value);
                    if (Number.isNaN(v)) return ['-', name];
                    if (name === 'USD/KRW') return [formatNumber(v, locale, 2), name];
                    if (name === t('macroScore')) return [formatPercent(v), name];
                    return [String(value), name];
                  }}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  iconType="line"
                  wrapperStyle={{ fontSize: 11, paddingBottom: 4 }}
                />
                <Line
                  yAxisId="fx"
                  type="monotone"
                  dataKey="fx_value"
                  name="USD/KRW"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
                <Line
                  yAxisId="score"
                  type="monotone"
                  dataKey="macro_score"
                  name={t('macroScore')}
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="5 3"
                  dot={false}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* Futures OHLCV Chart */}
      <Card>
        <h3 className="mb-4 text-base font-semibold text-[var(--foreground)]">{t('futuresChartTitle')}</h3>
        {futuresOhlcv.isLoading ? (
          <p className="text-sm text-[var(--foreground-muted)]">{t('futuresChartLoading')}</p>
        ) : futuresOhlcv.isError || !futuresOhlcv.data?.data?.length ? (
          <p className="inline-flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
            <ShieldAlert className="h-4 w-4" />
            {t('futuresChartError')}
          </p>
        ) : (
          <CandleChart data={futuresOhlcv.data.data} height={320} showVolume showMA />
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

// ---------------------------------------------------------------------------
// Signal Contribution Bar
// ---------------------------------------------------------------------------

function signalLabel(value: number, t: (key: string) => string): string {
  // value in [-1, 1]. Negative = risk-on (buying pressure), positive = risk-off (selling pressure)
  if (value <= -0.7) return t('signalStrongBuy');
  if (value <= -0.3) return t('signalBuy');
  if (value >= 0.7) return t('signalStrongSell');
  if (value >= 0.3) return t('signalSell');
  return t('signalNeutral');
}

function SignalBar({ label, value, nullLabel, t }: { label: string; value: number | null; nullLabel: string; t: (key: string) => string }) {
  // value is in [-1, 1] range. Positive = risk-off contribution, negative = risk-on.
  const pct = value != null ? Math.abs(value) * 100 : 0;
  const isNull = value == null;
  const isPositive = (value ?? 0) >= 0;
  const desc = !isNull ? signalLabel(value!, t) : null;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--foreground-muted)]">{label}</span>
        <span className="font-mono text-[var(--foreground)]">
          {isNull ? nullLabel : (
            <span className="inline-flex items-center gap-1.5">
              <span>{value!.toFixed(2)}</span>
              <span className={`text-[10px] font-sans ${isPositive ? 'text-red-400' : 'text-emerald-400'}`}>{desc}</span>
            </span>
          )}
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-[var(--background)] overflow-hidden">
        <div
          className={`absolute top-0 h-full rounded-full transition-all ${
            isNull ? 'bg-gray-300 dark:bg-gray-600' : isPositive ? 'bg-red-400' : 'bg-emerald-400'
          }`}
          style={{ width: `${Math.min(pct, 100)}%`, left: 0 }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metric Card (enhanced)
// ---------------------------------------------------------------------------

function MetricCard({
  title,
  icon,
  value,
  unit,
  source,
  items,
  ageSec,
  ageLabel,
  staleLabel,
  interpretationText,
}: {
  title: string;
  icon: ReactNode;
  value: string;
  unit: string;
  source: string;
  items: { label: string; value: string }[];
  ageSec: number | null;
  ageLabel: string;
  staleLabel: string;
  interpretationText?: string;
}) {
  const isStale = ageSec != null && ageSec > STALE_THRESHOLD_SEC;

  return (
    <Card>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="inline-flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
            {icon}
            {title}
          </div>
          {isStale && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 dark:bg-amber-900/30 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-3 w-3" />
              {staleLabel}
            </span>
          )}
        </div>
        <p className="text-xl font-semibold text-[var(--foreground)]">
          {value}
          {/\d/.test(value) && (
            <span className="ml-1 text-sm font-normal text-[var(--foreground-muted)]">{unit}</span>
          )}
        </p>
        {items.map((item) => (
          <p key={item.label} className="text-sm text-[var(--foreground-muted)]">
            {item.label}: {item.value}
          </p>
        ))}
        {interpretationText && (
          <p className="text-xs italic text-[var(--foreground-muted)]">{interpretationText}</p>
        )}
        <div className="flex items-center justify-between">
          <p className={`text-xs ${isStale ? 'text-amber-600 dark:text-amber-400' : 'text-[var(--foreground-muted)]'}`}>
            {ageLabel}
          </p>
          <p className="text-[10px] text-[var(--foreground-muted)] opacity-60">{source}</p>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Market Entry Assessment
// ---------------------------------------------------------------------------

const ENTRY_STYLES: Record<string, { icon: typeof CheckCircle; text: string; bg: string }> = {
  buy_favorable: {
    icon: CheckCircle,
    text: 'text-emerald-700 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800',
  },
  wait: {
    icon: AlertTriangle,
    text: 'text-amber-700 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800',
  },
  caution: {
    icon: ShieldAlert,
    text: 'text-red-700 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800',
  },
};

function MarketEntryAssessment({
  entrySignal,
  fxInterp,
  futuresInterp,
  flowInterp,
  t,
}: {
  entrySignal: MacroEntrySignal | string;
  fxInterp: string;
  futuresInterp: string;
  flowInterp: string;
  t: ReturnType<typeof useTranslations>;
}) {
  const style = ENTRY_STYLES[entrySignal] ?? ENTRY_STYLES.wait;
  const Icon = style.icon;

  return (
    <div className={`rounded-xl border p-4 ${style.bg}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Icon className={`h-8 w-8 ${style.text}`} />
          <div>
            <h2 className="text-sm font-medium text-[var(--foreground-muted)]">{t('entryAssessment')}</h2>
            <p className={`text-2xl font-bold ${style.text}`}>
              {t(`entry_${entrySignal}`)}
            </p>
          </div>
        </div>
        <p className="text-sm text-[var(--foreground)]">
          {t(`entryDesc_${entrySignal}`)}
        </p>
      </div>
      <ul className="mt-3 space-y-1 text-sm text-[var(--foreground-muted)]">
        <li className="flex items-start gap-2">
          <TrendingUp className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {t(`interp_fx_${fxInterp}`)}
        </li>
        <li className="flex items-start gap-2">
          <CandlestickChart className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {t(`interp_futures_${futuresInterp}`)}
        </li>
        <li className="flex items-start gap-2">
          <Users className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {t(`interp_flow_${flowInterp}`)}
        </li>
      </ul>
    </div>
  );
}
