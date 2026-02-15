'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { X, Loader2, AlertCircle, TrendingUp, BarChart3 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useBacktestStrategies, useRunBacktest } from '@/hooks/useBacktest';
import type {
  BacktestStrategy,
  BacktestResponse,
} from '@/lib/api';
import MetricsCards from './MetricsCards';
import TradesTable from './TradesTable';

interface BacktestPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const PERIODS = [
  { value: '1mo', labelKey: 'period1m' },
  { value: '3mo', labelKey: 'period3m' },
  { value: '6mo', labelKey: 'period6m' },
  { value: '1y', labelKey: 'period1y' },
  { value: '2y', labelKey: 'period2y' },
  { value: '5y', labelKey: 'period5y' },
];

/**
 * Render an equity curve as an SVG polyline.
 * Uses viewBox so it scales to the container width while maintaining a fixed aspect ratio.
 */
function EquityCurve({ points }: { points: Array<{ date: string; equity: number }> }) {
  const t = useTranslations('backtest');
  if (!points || points.length < 2) return null;

  const width = 360;
  const height = 100;
  const padding = 4;

  const equities = points.map((p) => p.equity);
  const minVal = Math.min(...equities);
  const maxVal = Math.max(...equities);
  const range = maxVal - minVal || 1;

  const polylinePoints = points
    .map((p, i) => {
      const x = padding + (i / (points.length - 1)) * (width - padding * 2);
      const y =
        height - padding - ((p.equity - minVal) / range) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(' ');

  // Determine trend colour based on first vs last equity
  const isPositive = equities[equities.length - 1] >= equities[0];
  const strokeColor = isPositive ? '#10b981' : '#ef4444';
  const fillColor = isPositive
    ? 'rgba(16,185,129,0.08)'
    : 'rgba(239,68,68,0.08)';

  // Build area path (fill under the curve)
  const areaPath = `M ${padding},${height - padding} ${points
    .map((p, i) => {
      const x = padding + (i / (points.length - 1)) * (width - padding * 2);
      const y =
        height - padding - ((p.equity - minVal) / range) * (height - padding * 2);
      return `L ${x},${y}`;
    })
    .join(' ')} L ${width - padding},${height - padding} Z`;

  return (
    <div className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] p-3">
      <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
        {t('equityCurve')}
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        preserveAspectRatio="none"
      >
        <path d={areaPath} fill={fillColor} />
        <polyline
          points={polylinePoints}
          fill="none"
          stroke={strokeColor}
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
      <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-500 mt-1 px-0.5">
        <span>{points[0].date.slice(0, 10)}</span>
        <span>{points[points.length - 1].date.slice(0, 10)}</span>
      </div>
    </div>
  );
}

/**
 * Trade summary strip shown between metrics and equity curve.
 */
function TradeSummary({
  numTrades,
  avgTradeReturn,
  maxConsecutiveWins,
  maxConsecutiveLosses,
}: {
  numTrades: number;
  avgTradeReturn: number;
  maxConsecutiveWins: number;
  maxConsecutiveLosses: number;
}) {
  const t = useTranslations('backtest');
  return (
    <div className="grid grid-cols-2 gap-2.5">
      <div className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2">
        <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
          {t('trades')}
        </div>
        <div className="text-sm font-bold text-gray-900 dark:text-gray-100">
          {numTrades}
        </div>
      </div>
      <div className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2">
        <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
          {t('avgReturn')}
        </div>
        <div
          className={`text-sm font-bold ${
            avgTradeReturn >= 0
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-red-600 dark:text-red-400'
          }`}
        >
          {avgTradeReturn >= 0 ? '+' : ''}
          {(avgTradeReturn * 100).toFixed(2)}%
        </div>
      </div>
      <div className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2">
        <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
          {t('maxConsecWins')}
        </div>
        <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
          {maxConsecutiveWins}
        </div>
      </div>
      <div className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2">
        <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
          {t('maxConsecLosses')}
        </div>
        <div className="text-sm font-bold text-red-600 dark:text-red-400">
          {maxConsecutiveLosses}
        </div>
      </div>
    </div>
  );
}

export default function BacktestPanel({ isOpen, onClose }: BacktestPanelProps) {
  const t = useTranslations('backtest');
  // --- Form state ---
  const [ticker, setTicker] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [period, setPeriod] = useState('1y');
  const [cash, setCash] = useState(10_000_000);
  const [strategyParams, setStrategyParams] = useState<Record<string, unknown>>({});

  // --- Results ---
  const [result, setResult] = useState<BacktestResponse | null>(null);

  // --- Queries & mutations ---
  const { data: strategiesData, isLoading: strategiesLoading } =
    useBacktestStrategies();
  const runBacktest = useRunBacktest();

  // Resolved strategy metadata
  const strategies: BacktestStrategy[] = useMemo(
    () => strategiesData?.strategies ?? [],
    [strategiesData]
  );

  const currentStrategy = useMemo(
    () => strategies.find((s) => s.name === selectedStrategy) ?? null,
    [strategies, selectedStrategy]
  );

  // When strategy list arrives and nothing is selected, pick the first
  useEffect(() => {
    if (strategies.length > 0 && !selectedStrategy) {
      setSelectedStrategy(strategies[0].name);
    }
  }, [strategies, selectedStrategy]);

  // Reset strategy params when strategy selection changes
  const prevStrategyRef = useRef(selectedStrategy);
  useEffect(() => {
    if (selectedStrategy && selectedStrategy !== prevStrategyRef.current) {
      prevStrategyRef.current = selectedStrategy;
      if (currentStrategy) {
        const defaults: Record<string, unknown> = {};
        for (const p of currentStrategy.params) {
          defaults[p.name] = p.default;
        }
        setStrategyParams(defaults);
      }
    }
  }, [selectedStrategy, currentStrategy]);

  // --- Handlers ---
  const handleRun = useCallback(() => {
    if (!ticker.trim() || !selectedStrategy) return;
    setResult(null);
    runBacktest.mutate(
      {
        ticker: ticker.trim(),
        strategy: selectedStrategy,
        period,
        cash,
        strategy_params:
          Object.keys(strategyParams).length > 0 ? strategyParams : undefined,
      },
      {
        onSuccess: (data) => {
          setResult(data);
        },
      }
    );
  }, [ticker, selectedStrategy, period, cash, strategyParams, runBacktest]);

  const handleStrategyChange = useCallback(
    (name: string) => {
      setSelectedStrategy(name);
      setResult(null);
    },
    []
  );

  const handleParamChange = useCallback(
    (paramName: string, value: unknown) => {
      setStrategyParams((prev) => ({ ...prev, [paramName]: value }));
    },
    []
  );

  // --- Shared input classes (matches PropertiesPanel) ---
  const inputCls =
    'w-full rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none focus:border-[#1313ec] focus:ring-1 focus:ring-[#1313ec]/20 transition-colors';

  // If panel is closed, render nothing
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20 dark:bg-black/40"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-[420px] max-w-full flex flex-col bg-white dark:bg-[#0b0b0c] border-l border-[#e1e3e5] dark:border-[#2e2e30] shadow-xl animate-in slide-in-from-right">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[#1313ec]" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {t('title')}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="h-4 w-4 text-gray-400" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* ---- FORM SECTION ---- */}
          <section className="space-y-4">
            {/* Ticker */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">
                {t('ticker')}
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder={t('tickerPlaceholder')}
                className={inputCls}
              />
            </div>

            {/* Strategy selector */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">
                {t('strategy')}
              </label>
              {strategiesLoading ? (
                <div className="flex items-center gap-2 text-xs text-gray-400 py-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {t('loadingStrategies')}
                </div>
              ) : (
                <select
                  value={selectedStrategy}
                  onChange={(e) => handleStrategyChange(e.target.value)}
                  className={inputCls}
                >
                  {strategies.map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.label}
                    </option>
                  ))}
                </select>
              )}
              {currentStrategy?.description && (
                <p className="mt-1.5 text-[11px] text-gray-400 dark:text-gray-500 leading-relaxed">
                  {currentStrategy.description}
                </p>
              )}
            </div>

            {/* Period */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">
                {t('period')}
              </label>
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className={inputCls}
              >
                {PERIODS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {t(p.labelKey)}
                  </option>
                ))}
              </select>
            </div>

            {/* Initial Cash */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">
                {t('initialCash')}
              </label>
              <input
                type="number"
                value={cash}
                onChange={(e) => setCash(Number(e.target.value))}
                className={inputCls}
              />
            </div>

            {/* Dynamic strategy params */}
            {currentStrategy && currentStrategy.params.length > 0 && (
              <div className="space-y-3">
                <div className="text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                  {t('strategyParams')}
                </div>
                {currentStrategy.params.map((param) => (
                  <div key={param.name}>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                      {param.description || param.name}
                    </label>
                    {param.type === 'bool' ? (
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(
                            strategyParams[param.name] ?? param.default
                          )}
                          onChange={(e) =>
                            handleParamChange(param.name, e.target.checked)
                          }
                          className="rounded border-[#e1e3e5] dark:border-[#2e2e30] text-[#1313ec] focus:ring-[#1313ec]/20"
                        />
                        <span className="text-gray-600 dark:text-gray-300">
                          {Boolean(strategyParams[param.name] ?? param.default)
                            ? t('enabled')
                            : t('disabled')}
                        </span>
                      </label>
                    ) : param.type === 'str' ? (
                      <input
                        type="text"
                        value={String(
                          strategyParams[param.name] ?? param.default ?? ''
                        )}
                        onChange={(e) =>
                          handleParamChange(param.name, e.target.value)
                        }
                        className={inputCls}
                      />
                    ) : (
                      <input
                        type="number"
                        step={param.type === 'float' ? '0.01' : '1'}
                        value={
                          strategyParams[param.name] !== undefined &&
                          strategyParams[param.name] !== null
                            ? String(strategyParams[param.name])
                            : String(param.default ?? '')
                        }
                        onChange={(e) => {
                          const raw = e.target.value;
                          if (raw === '') {
                            handleParamChange(param.name, null);
                          } else {
                            handleParamChange(
                              param.name,
                              param.type === 'int'
                                ? parseInt(raw, 10)
                                : parseFloat(raw)
                            );
                          }
                        }}
                        className={inputCls}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Run button */}
            <button
              type="button"
              onClick={handleRun}
              disabled={
                runBacktest.isPending || !ticker.trim() || !selectedStrategy
              }
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#1313ec] text-white text-sm font-semibold hover:bg-[#1010c0] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {runBacktest.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('running')}
                </>
              ) : (
                <>
                  <TrendingUp className="h-4 w-4" />
                  {t('runBacktest')}
                </>
              )}
            </button>
          </section>

          {/* ---- ERROR STATE ---- */}
          {runBacktest.isError && (
            <div className="rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 p-3 flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
              <div className="text-sm text-red-700 dark:text-red-300">
                {runBacktest.error instanceof Error
                  ? runBacktest.error.message
                  : t('failed')}
              </div>
            </div>
          )}

          {/* ---- LOADING STATE ---- */}
          {runBacktest.isPending && (
            <div className="flex flex-col items-center justify-center py-10 text-gray-400 dark:text-gray-500">
              <Loader2 className="h-8 w-8 animate-spin mb-3" />
              <span className="text-sm">{t('running')}</span>
              <span className="text-xs mt-1">{t('runningNote')}</span>
            </div>
          )}

          {/* ---- RESULTS SECTION ---- */}
          {result && (
            <section className="space-y-5 pb-4">
              {/* Result header */}
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-[#1313ec]" />
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {t('results')}
                </span>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {result.ticker} / {result.strategy} / {result.period}
                </span>
              </div>

              {/* Metrics grid */}
              <MetricsCards metrics={result.metrics} />

              {/* Trade summary strip */}
              <TradeSummary
                numTrades={result.metrics.num_trades}
                avgTradeReturn={result.metrics.avg_trade_return}
                maxConsecutiveWins={result.metrics.max_consecutive_wins}
                maxConsecutiveLosses={result.metrics.max_consecutive_losses}
              />

              {/* Equity curve */}
              <EquityCurve points={result.equity_curve} />

              {/* Trades table */}
              {result.trades.length > 0 && (
                <div>
                  <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2">
                    {t('individualTrades')}
                  </div>
                  <TradesTable trades={result.trades} />
                </div>
              )}
            </section>
          )}
        </div>
      </div>
    </>
  );
}
