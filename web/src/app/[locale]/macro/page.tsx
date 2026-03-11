'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useMemo, useState, type ReactNode } from 'react';
import { Card } from '@/components/ui';
import { useMacroBundle, useMacroHistory, usePrefetchMacroHistory, useOhlcv } from '@/hooks/useMarket';
import CandleChart from '@/components/charts/CandleChart';
import { formatPercent } from '@/lib/format';
import {
  Activity,
  AlertTriangle,
  CandlestickChart,
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
import type { MacroRegime } from '@/lib/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatNumber(value: number | null, locale: string, maximumFractionDigits = 2): string {
  if (value == null || Number.isNaN(value)) return '-';
  return value.toLocaleString(locale === 'ko' ? 'ko-KR' : locale === 'zh' ? 'zh-CN' : 'en-US', {
    maximumFractionDigits,
  });
}

function formatAge(sec: number | null, t: (key: string, values?: Record<string, string | number>) => string): string {
  if (sec == null || Number.isNaN(sec)) return t('ageSec', { age: '-' });
  if (sec < 60) return t('ageSec', { age: `${Math.round(sec)}` });
  if (sec < 3600) return t('ageMin', { age: `${Math.round(sec / 60)}` });
  if (sec < 86400) return t('ageHour', { age: `${(sec / 3600).toFixed(1)}` });
  return t('ageDay', { age: `${(sec / 86400).toFixed(1)}` });
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

function getSignalContributions(signal: { reason_detail?: { components: { fx: { raw: number }; futures: { raw: number }; flow: { raw: number } } } | null; reason?: string | null }): { fx: number | null; futures: number | null; flow: number | null } {
  // Prefer structured reason_detail
  const detail = signal.reason_detail;
  if (detail?.components) {
    return {
      fx: detail.components.fx?.raw ?? null,
      futures: detail.components.futures?.raw ?? null,
      flow: detail.components.flow?.raw ?? null,
    };
  }
  // Fallback: parse legacy reason string
  const reason = signal.reason;
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

type WindowOption = '60m' | '6h' | '1d' | '7d' | '30d';

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function MacroPage() {
  const t = useTranslations('macro');
  const locale = useLocale();
  const bundleQuery = useMacroBundle();
  const [historyWindow, setHistoryWindow] = useState<WindowOption>('60m');
  const historyQuery = useMacroHistory(historyWindow);
  usePrefetchMacroHistory(); // prefetch all windows on mount for instant tab switching
  const futuresTicker = bundleQuery.data?.futures.symbol || '069500.KS';
  const futuresOhlcv = useOhlcv(futuresTicker, 30);

  const regime = bundleQuery.data?.signal.regime ?? 'unknown';
  const interpretation = bundleQuery.data?.interpretation;

  const contributions = useMemo(
    () => getSignalContributions(bundleQuery.data?.signal ?? {}),
    [bundleQuery.data?.signal],
  );

  // Compute change% from first data point for each history point
  const chartData = useMemo(() => {
    const points = historyQuery.data?.points ?? [];
    if (points.length === 0) return [];
    const baseFx = points[0].fx_value;
    return points.map((p) => ({
      ...p,
      fx_change_pct: p.fx_value != null && baseFx != null && baseFx !== 0
        ? ((p.fx_value - baseFx) / baseFx) * 100
        : null,
    }));
  }, [historyQuery.data?.points]);

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

      {/* Gauge Hero — Regime + Entry Assessment unified */}
      <div className="rounded-xl border border-[var(--border)] bg-gradient-to-b from-slate-900 to-slate-800 dark:from-slate-950 dark:to-slate-900 p-6 text-white">
        <div className="flex flex-col items-center gap-6 lg:flex-row lg:items-start lg:gap-10">
          {/* Gauge */}
          <div className="flex flex-col items-center">
            <RegimeGauge
              score={bundleQuery.data?.signal.macro_score ?? null}
              regime={regime}
              t={t}
            />
            <p className="mt-2 text-xs text-slate-300">
              {formatDateTime(bundleQuery.data?.signal.updated_at ?? null, locale)}
            </p>
          </div>

          {/* Right panel: Entry signal + Insight + Signal bars */}
          <div className="flex-1 space-y-4 text-center lg:text-left">
            {/* Entry signal badge */}
            {interpretation && (
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{t('entryAssessment')}</p>
                <p className={`text-2xl font-bold ${
                  interpretation.entry_signal === 'buy_favorable' ? 'text-emerald-400' :
                  interpretation.entry_signal === 'caution' ? 'text-red-400' : 'text-amber-400'
                }`}>
                  {t(`entry_${interpretation.entry_signal}`)}
                </p>
                <p className="text-sm text-slate-300">
                  {t(`entryDesc_${interpretation.entry_signal}`)}
                </p>
              </div>
            )}

            {/* Regime insight text */}
            <p className="text-sm text-slate-300">
              {t(`insight${regime === 'risk_on' ? 'RiskOn' : regime === 'risk_off' ? 'RiskOff' : regime === 'neutral' ? 'Neutral' : 'Unknown'}`)}
            </p>

            {/* Interpretation bullets */}
            {interpretation && (
              <ul className="space-y-1 text-sm text-slate-400">
                <li className="flex items-start gap-2">
                  <TrendingUp className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                  {t(`interp_fx_${interpretation.fx_interpretation}`)}
                </li>
                <li className="flex items-start gap-2">
                  <CandlestickChart className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                  {t(`interp_futures_${interpretation.futures_interpretation}`)}
                </li>
                <li className="flex items-start gap-2">
                  <Users className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                  {t(`interp_flow_${interpretation.flow_interpretation}`)}
                </li>
              </ul>
            )}

            {/* Signal Contribution Bars */}
            <div className="space-y-1 pt-2">
              <div className="flex items-center justify-between text-xs text-slate-400 px-0.5">
                <span>{t('signalLegendBuy')}</span>
                <span>{t('signalLegendSell')}</span>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <SignalBar label={t('fxSignal')} value={contributions.fx} nullLabel={t('flowUnavailable')} t={t} />
                <SignalBar label={t('futuresSignal')} value={contributions.futures} nullLabel={t('flowUnavailable')} t={t} />
                <SignalBar label={t('flowSignal')} value={contributions.flow} nullLabel={t('flowUnavailable')} t={t} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid gap-4 lg:grid-cols-3">
        <MetricCard
          title="USD/KRW"
          icon={<DollarSign className="h-4 w-4" />}
          value={formatNumber(bundleQuery.data?.fx.value ?? null, locale, 2)}
          unit={t('fxUnit')}
          changePct={bundleQuery.data?.fx.change_pct ?? null}
          source={t('fxSource')}
          items={[]}
          ageSec={bundleQuery.data?.freshness.fx_age_sec ?? null}
          ageLabel={formatAge(bundleQuery.data?.freshness.fx_age_sec ?? null, t)}
          staleLabel={t('staleWarning')}
          interpretationText={interpretation ? t(`interp_fx_${interpretation.fx_interpretation}`) : undefined}
        />
        <MetricCard
          title={t('futures')}
          icon={<CandlestickChart className="h-4 w-4" />}
          value={formatNumber(bundleQuery.data?.futures.value ?? null, locale, 0)}
          unit={t('futuresUnit')}
          changePct={bundleQuery.data?.futures.change_pct ?? null}
          source={t('futuresSource')}
          items={[
            { label: t('basis'), value: bundleQuery.data?.futures.basis != null ? `${bundleQuery.data.futures.basis > 0 ? '+' : ''}${formatNumber(bundleQuery.data.futures.basis, locale, 3)}%` : '-', hint: t('basisExplain') },
          ]}
          ageSec={bundleQuery.data?.freshness.futures_age_sec ?? null}
          ageLabel={formatAge(bundleQuery.data?.freshness.futures_age_sec ?? null, t)}
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
            { label: t('foreign'), value: formatFlowBillion(bundleQuery.data?.flow.foreign_net ?? null, locale) },
            { label: t('institution'), value: formatFlowBillion(bundleQuery.data?.flow.institution_net ?? null, locale) },
            { label: t('individual'), value: formatFlowBillion(bundleQuery.data?.flow.individual_net ?? null, locale) },
          ]}
          ageSec={bundleQuery.data?.freshness.flow_age_sec ?? null}
          ageLabel={formatAge(bundleQuery.data?.freshness.flow_age_sec ?? null, t)}
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
            {(['60m', '6h', '1d', '7d', '30d'] as WindowOption[]).map((w) => {
              const labelMap: Record<WindowOption, string> = { '60m': '1h', '6h': '6h', '1d': '1d', '7d': '1w', '30d': '1m' };
              return (
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
                  {t(`window${labelMap[w]}`)}
                </button>
              );
            })}
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
              <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
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
                    if (name === t('fxChangePct')) return [`${v > 0 ? '+' : ''}${v.toFixed(3)}%`, name];
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
                <Line
                  yAxisId="score"
                  type="monotone"
                  dataKey="fx_change_pct"
                  name={t('fxChangePct')}
                  stroke="#8b5cf6"
                  strokeWidth={1.5}
                  strokeDasharray="3 2"
                  dot={false}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
        {(() => {
          const pts = historyQuery.data?.points ?? [];
          if (pts.length < 2) return null;
          // Show how much data we actually have vs requested
          const windowMinutes: Record<WindowOption, number> = { '60m': 60, '6h': 360, '1d': 1440, '7d': 10080, '30d': 43200 };
          const first = new Date(pts[0].timestamp).getTime();
          const last = new Date(pts[pts.length - 1].timestamp).getTime();
          const spanMin = (last - first) / 60000;
          const requested = windowMinutes[historyWindow];
          if (spanMin < requested * 0.8) {
            return (
              <p className="mt-2 text-center text-xs text-[var(--foreground-muted)]">
                {t('dataRangeHint', { actual: spanMin < 60 ? `${Math.round(spanMin)}m` : `${(spanMin / 60).toFixed(1)}h`, requested: historyWindow === '60m' ? '1h' : historyWindow === '6h' ? '6h' : historyWindow === '1d' ? '1d' : historyWindow === '7d' ? '1w' : '1m' })}
              </p>
            );
          }
          // Check if values are flat (market closed)
          const fxVals = pts.map(p => p.fx_value).filter((v): v is number => v != null);
          if (fxVals.length >= 2 && new Set(fxVals).size === 1) {
            return (
              <p className="mt-2 text-center text-xs text-[var(--foreground-muted)]">
                {t('marketClosedHint')}
              </p>
            );
          }
          return null;
        })()}
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
          <CandleChart data={futuresOhlcv.data.data} height={320} showVolume showChangeRate showMA />
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
// Regime Gauge — semicircular speedometer
// ---------------------------------------------------------------------------

function RegimeGauge({
  score,
  regime,
  t,
}: {
  score: number | null;
  regime: MacroRegime | string;
  t: (key: string) => string;
}) {
  // Map score from [-1, 1] to angle for the semicircle
  // -1 = full left (risk_off/red), 0 = center (neutral/amber), +1 = full right (risk_on/green)
  const hasScore = score != null;
  const clampedScore = hasScore ? Math.max(-1, Math.min(1, score)) : 0;
  const needleAngle = clampedScore * 90; // -90° to +90° from center
  // Signed percentage consistent with history chart (-100% to +100%)
  const displayPct = Math.round(clampedScore * 100);
  const displayLabel = hasScore ? `${displayPct > 0 ? '+' : ''}${displayPct}%` : '-';

  const regimeColor = regime === 'risk_on' ? 'text-emerald-400' :
    regime === 'risk_off' ? 'text-red-400' : 'text-amber-400';

  return (
    <div className="relative flex flex-col items-center" role="meter" aria-label={hasScore ? `Macro score: ${displayPct}%` : 'Macro score unavailable'} aria-valuemin={-100} aria-valuemax={100} aria-valuenow={hasScore ? displayPct : undefined}>
      {/* Gauge arc */}
      <div className="relative h-[100px] w-[200px] overflow-hidden">
        <div
          className="absolute inset-0 h-[200px] w-[200px] rounded-full"
          style={{
            background: 'conic-gradient(from 180deg, #ef4444 0deg, #ef4444 54deg, #f59e0b 54deg, #f59e0b 126deg, #10b981 126deg, #10b981 180deg, transparent 180deg)',
          }}
        />
        {/* Inner cutout — creates the arc ring */}
        <div className="absolute left-1/2 top-0 h-[200px] w-[200px] -translate-x-1/2 scale-[0.7] rounded-full bg-slate-900" />
        {/* Needle — hidden when no data */}
        <div
          className={`absolute bottom-0 left-1/2 h-[90px] w-0.5 origin-bottom transition-transform duration-700 ease-out ${hasScore ? '' : 'opacity-20'}`}
          style={{ transform: `translateX(-50%) rotate(${needleAngle}deg)` }}
        >
          <div className="h-full w-full rounded-full bg-white" />
          <div className="absolute -bottom-1 left-1/2 h-3 w-3 -translate-x-1/2 rounded-full border-2 border-white bg-slate-900" />
        </div>
      </div>

      {/* Score display below gauge */}
      <div className="mt-1 text-center">
        <span className={`text-3xl font-bold ${regimeColor}`}>{displayLabel}</span>
        <p className={`text-sm font-semibold uppercase tracking-wide ${regimeColor}`}>
          {t(`regime_${regime}`)}
        </p>
      </div>

      {/* Scale labels */}
      <div className="flex w-[200px] justify-between px-1 text-xs text-slate-400">
        <span>{t('regimeRiskOff')}</span>
        <span>{t('regimeNeutral')}</span>
        <span>{t('regimeRiskOn')}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Signal Contribution Bar
// ---------------------------------------------------------------------------

function signalLabel(value: number, t: (key: string) => string): string {
  if (value <= -0.7) return t('signalStrongBuy');
  if (value <= -0.3) return t('signalBuy');
  if (value >= 0.7) return t('signalStrongSell');
  if (value >= 0.3) return t('signalSell');
  return t('signalNeutral');
}

function SignalBar({ label, value, nullLabel, t }: { label: string; value: number | null; nullLabel: string; t: (key: string) => string }) {
  const pct = value != null ? Math.min(Math.abs(value) * 50, 50) : 0;
  const isNull = value == null;
  const isBuy = (value ?? 0) < 0;
  const desc = !isNull ? signalLabel(value!, t) : null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        {isNull ? (
          <span className="text-slate-500">{nullLabel}</span>
        ) : (
          <span className={`font-medium ${isBuy ? 'text-emerald-400' : 'text-red-400'}`}>{desc}</span>
        )}
      </div>
      <div className="relative h-2.5 rounded-full bg-slate-700 overflow-hidden">
        <div className="absolute left-1/2 top-0 h-full w-px bg-slate-500 opacity-40" />
        {!isNull && pct > 0 && (
          <div
            className={`absolute top-0 h-full rounded-full transition-all ${
              isBuy ? 'bg-emerald-400' : 'bg-red-400'
            }`}
            style={
              isBuy
                ? { right: '50%', width: `${pct}%` }
                : { left: '50%', width: `${pct}%` }
            }
          />
        )}
        {isNull && (
          <div
            className="absolute top-0 h-full rounded-full bg-slate-600"
            style={{ left: '50%', width: '2%', transform: 'translateX(-50%)' }}
          />
        )}
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
  changePct,
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
  changePct?: number | null;
  source: string;
  items: { label: string; value: string; hint?: string }[];
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
        <div className="flex items-baseline gap-2">
          <p className="text-xl font-semibold text-[var(--foreground)]">
            {value}
            {/\d/.test(value) && (
              <span className="ml-1 text-sm font-normal text-[var(--foreground-muted)]">{unit}</span>
            )}
          </p>
          {changePct != null && (
            <span className={`text-sm font-medium ${changePct > 0 ? 'text-red-500' : changePct < 0 ? 'text-emerald-500' : 'text-[var(--foreground-muted)]'}`}>
              {changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%
            </span>
          )}
        </div>
        {items.map((item) => (
          <div key={item.label} className="space-y-0.5">
            <p className="text-sm text-[var(--foreground-muted)]">
              {item.label}: {item.value}
            </p>
            {item.hint && (
              <p className="text-[10px] text-[var(--foreground-muted)] opacity-60">{item.hint}</p>
            )}
          </div>
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

