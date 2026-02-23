'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { routing } from '@/i18n/routing';
import {
  ArrowLeft,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Building2,
  DollarSign,
  Percent,
  PieChart,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Brain,
  ShieldAlert,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Banknote,
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { CandleChart, IndicatorPanel } from '@/components/charts';
import {
  getTickerAnalysis,
  analyzeStock,
  checkStockConditions,
  getAnalysisStatus,
  getPresets,
} from '@/lib/api';
import type {
  TickerAnalysis,
  AIAnalysisResult,
  ScreeningResult,
  ConditionResult,
  PresetInfo,
} from '@/lib/types';

type PeriodOption = '1mo' | '3mo' | '6mo' | '1y' | '2y';

const periodOptions: { value: PeriodOption; label: string }[] = [
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '2y', label: '2Y' },
];

const LOCALE_SYNC_KEY = 'quant-investment:locale-sync';

function toTitleCaseFromKey(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/** Collapsible section wrapper – in popup mode sections start collapsed. */
function CollapsibleSection({
  title,
  expanded,
  onToggle,
  isPopup,
  headerRight,
  children,
}: {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  isPopup: boolean;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}) {
  // In non-popup mode, always show content (no toggle)
  if (!isPopup) {
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-[var(--foreground)]">{title}</h2>
          {headerRight}
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className="border border-[var(--border)] rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center justify-between w-full px-4 py-3 text-left bg-[var(--background-secondary)] hover:bg-[var(--background)] transition-colors"
      >
        <h2 className="text-sm font-semibold text-[var(--foreground)]">{title}</h2>
        <div className="flex items-center gap-2">
          {headerRight}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-[var(--foreground-muted)]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[var(--foreground-muted)]" />
          )}
        </div>
      </button>
      {expanded && <div className="p-4">{children}</div>}
    </div>
  );
}

/**
 * Dynamic ticker analysis page with full chart, indicators,
 * strategy context, AI insight, and sector distribution.
 */
export default function TickerAnalysisPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const locale = useLocale();
  const isPopup = searchParams.get('popup') === 'true';
  const ticker = params.ticker as string;
  const t = useTranslations('stockDetail');
  const tCommon = useTranslations('common');
  const tConditions = useTranslations('conditions');
  const tScreening = useTranslations('screening');

  // Core data
  const [tickerData, setTickerData] = useState<TickerAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodOption>('6mo');

  // Strategy Context
  const [screeningResult, setScreeningResult] = useState<ScreeningResult | null>(null);
  const [screeningLoading, setScreeningLoading] = useState(false);
  const [screeningError, setScreeningError] = useState<string | null>(null);
  const [presets, setPresets] = useState<PresetInfo[]>([]);
  const [selectedPreset, setSelectedPreset] = useState('accumulation_basic');

  // AI Insight
  const [aiResult, setAiResult] = useState<AIAnalysisResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiAvailable, setAiAvailable] = useState<boolean | null>(null);
  const [reasoningExpanded, setReasoningExpanded] = useState(false);

  const fetchData = useCallback(async (period: PeriodOption) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getTickerAnalysis(ticker.toUpperCase(), period);
      setTickerData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('loadFailed'));
      setTickerData(null);
    } finally {
      setIsLoading(false);
    }
  }, [ticker, t]);

  // Fetch presets on mount
  useEffect(() => {
    getPresets()
      .then(setPresets)
      .catch(() => {});
  }, []);

  // Fetch screening conditions
  const fetchScreening = useCallback(async (preset?: string) => {
    setScreeningLoading(true);
    setScreeningError(null);
    try {
      const result = await checkStockConditions(ticker.toUpperCase(), preset || selectedPreset);
      setScreeningResult(result);
    } catch (err) {
      setScreeningError(err instanceof Error ? err.message : t('screeningError'));
    } finally {
      setScreeningLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- selectedPreset is read as fallback only; preset is always passed explicitly from the dropdown onChange handler
  }, [ticker, t]);

  // Check AI availability on mount
  useEffect(() => {
    getAnalysisStatus()
      .then((status) => setAiAvailable(status.claude_available))
      .catch(() => setAiAvailable(false));
  }, []);

  // Keep popup locale in sync with the main window locale changes.
  useEffect(() => {
    if (!isPopup) return;

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== LOCALE_SYNC_KEY || !event.newValue) return;

      try {
        const payload = JSON.parse(event.newValue) as { locale?: string };
        const nextLocale = payload.locale;
        if (!nextLocale || nextLocale === locale) return;
        if (!routing.locales.includes(nextLocale as (typeof routing.locales)[number])) return;
        window.location.replace(`/${nextLocale}/analysis/${encodeURIComponent(ticker)}?popup=true`);
      } catch {
        // Ignore malformed payloads.
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [isPopup, locale, ticker]);

  // Effect 1: Fetch main page data (chart, indicators, financials)
  useEffect(() => {
    if (ticker) fetchData(selectedPeriod);
  }, [ticker, selectedPeriod, fetchData]);

  // Effect 2: Fetch screening data (strategy context only)
  useEffect(() => {
    if (ticker) fetchScreening();
  }, [ticker, fetchScreening]);

  const handlePeriodChange = (period: PeriodOption) => {
    setSelectedPeriod(period);
  };

  const handleAIAnalysis = async () => {
    setAiLoading(true);
    setAiError(null);
    try {
      const result = await analyzeStock(ticker.toUpperCase());
      setAiResult(result);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : t('aiAnalysisError'));
    } finally {
      setAiLoading(false);
    }
  };

  const formatMarketCap = (value: number): string => {
    if (value >= 1_000_000_000_000) {
      return `$${(value / 1_000_000_000_000).toFixed(2)}T`;
    }
    if (value >= 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(2)}B`;
    }
    if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    }
    return `$${value.toLocaleString()}`;
  };

  const getConditionIcon = (condition: ConditionResult) => {
    if (condition.matched) {
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    }
    return <XCircle className="h-4 w-4 text-red-500" />;
  };

  const getConditionBadge = (condition: ConditionResult) => {
    if (condition.matched) {
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          {t('pass')}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
        {t('fail')}
      </span>
    );
  };

  const getRecommendationStyle = (rec: string) => {
    switch (rec) {
      case 'BUY':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'WAIT':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200';
      case 'AVOID':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getRecommendationLabel = (rec: string) => {
    switch (rec) {
      case 'BUY':
        return t('recommendationBuy');
      case 'WAIT':
        return t('recommendationWait');
      case 'AVOID':
        return t('recommendationAvoid');
      default:
        return rec;
    }
  };

  const getScoreColor = (score: number, invert = false) => {
    const effectiveScore = invert ? 11 - score : score;
    if (effectiveScore >= 7) return 'text-green-600 dark:text-green-400';
    if (effectiveScore >= 4) return 'text-amber-600 dark:text-amber-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getScoreBarColor = (score: number, invert = false) => {
    const effectiveScore = invert ? 11 - score : score;
    if (effectiveScore >= 7) return 'bg-green-500';
    if (effectiveScore >= 4) return 'bg-amber-500';
    return 'bg-red-500';
  };

  // Collapsible section state for popup mode
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    indicators: !isPopup,
    financials: !isPopup,
    strategy: false,
    ai: false,
    sector: false,
    priceSummary: false,
  });

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className={isPopup ? 'space-y-3' : 'space-y-6'}>
      {/* Popup header bar */}
      {isPopup && (
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 px-1 py-2 bg-[var(--background)] border-b border-[var(--border)]">
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-lg font-bold text-[var(--foreground)] truncate">
              {ticker.toUpperCase()}
            </h1>
            {tickerData && (
              <>
                <span className="text-lg font-semibold text-[var(--foreground)]">
                  ${tickerData.current_price.toFixed(2)}
                </span>
                <span
                  className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold ${
                    tickerData.change_pct >= 0
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  }`}
                >
                  {tickerData.change_pct >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {tickerData.change_pct >= 0 ? '+' : ''}{tickerData.change_pct.toFixed(2)}%
                </span>
              </>
            )}
            {tickerData && (
              <span className="text-sm text-[var(--foreground-muted)] truncate">
                {tickerData.name}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => window.close()}
            className="shrink-0 p-1.5 rounded-lg hover:bg-[var(--background-secondary)] text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
            aria-label={tCommon('close')}
          >
            <XCircle className="h-5 w-5" />
          </button>
        </div>
      )}

      {/* Back navigation - hidden in popup mode */}
      {!isPopup && (
        <Link
          href="/analysis"
          className="inline-flex items-center gap-2 text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('backToAnalysis')}
        </Link>
      )}

      {/* Header - full version for non-popup */}
      {!isPopup && (
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="rounded-lg bg-[var(--color-primary)] p-3">
              <BarChart3 className="h-8 w-8 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-[var(--foreground)]">
                  {ticker.toUpperCase()}
                </h1>
                {tickerData && (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${
                      tickerData.change_pct >= 0
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}
                  >
                    {tickerData.change_pct >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    {tickerData.change_pct >= 0 ? '+' : ''}
                    {tickerData.change_pct.toFixed(2)}%
                  </span>
                )}
              </div>
              {tickerData && (
                <p className="text-[var(--foreground-muted)] mt-1">
                  {tickerData.name}
                </p>
              )}
            </div>
          </div>

          {tickerData && (
            <div className="text-right">
              <span className="text-3xl font-bold text-[var(--foreground)]">
                ${tickerData.current_price.toFixed(2)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-4">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] h-[500px] flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="animate-spin rounded-full h-10 w-10 border-3 border-[var(--color-primary)] border-t-transparent" />
              <span className="text-[var(--foreground-muted)]">
                {t('loadingData', { ticker: ticker.toUpperCase() })}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <Card padding="lg" className="text-center">
          <div className="flex flex-col items-center">
            <BarChart3 className="h-12 w-12 text-red-500 mb-4" />
            <h3 className="text-lg font-medium text-[var(--foreground)]">
              {t('loadFailed')}
            </h3>
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => fetchData(selectedPeriod)}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              {t('retry')}
            </Button>
          </div>
        </Card>
      )}

      {/* Main Content */}
      {tickerData && !isLoading && (
        <>
          {/* Period Selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-[var(--foreground-muted)]">
              {t('period')}:
            </span>
            <div className="flex rounded-lg border border-[var(--border)] overflow-hidden">
              {periodOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handlePeriodChange(option.value)}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    selectedPeriod === option.value
                      ? 'bg-[var(--color-primary)] text-white'
                      : 'bg-[var(--background-secondary)] text-[var(--foreground)] hover:bg-[var(--background)]'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Chart */}
          <CandleChart
            data={tickerData.ohlcv}
            height={isPopup ? 340 : 500}
            showVolume={true}
          />

          {/* Technical Indicators */}
          <CollapsibleSection
            title={t('technicalIndicators')}
            expanded={expandedSections.indicators}
            onToggle={() => toggleSection('indicators')}
            isPopup={isPopup}
          >
            <IndicatorPanel technicalData={tickerData.technical} />
          </CollapsibleSection>

          {/* ===== Financial Overview ===== */}
          {tickerData.fundamental && (
            <CollapsibleSection
              title={t('financialOverview')}
              expanded={expandedSections.financials}
              onToggle={() => toggleSection('financials')}
              isPopup={isPopup}
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                {/* Market Cap */}
                <Card padding="md">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-[var(--background)] p-2">
                      <DollarSign className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                    <div>
                      <span className="text-xs text-[var(--foreground-muted)]">
                        {t('marketCap')}
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)]">
                        {formatMarketCap(tickerData.fundamental.market_cap)}
                      </p>
                    </div>
                  </div>
                </Card>

                {/* P/E Ratio */}
                <Card padding="md">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-[var(--background)] p-2">
                      <PieChart className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                    <div>
                      <span className="text-xs text-[var(--foreground-muted)]">
                        {t('peRatio')}
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)]">
                        {tickerData.fundamental.pe_ratio !== null
                          ? tickerData.fundamental.pe_ratio.toFixed(2)
                          : t('notAvailable')}
                      </p>
                    </div>
                  </div>
                </Card>

                {/* Dividend Yield */}
                <Card padding="md">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-[var(--background)] p-2">
                      <Percent className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                    <div>
                      <span className="text-xs text-[var(--foreground-muted)]">
                        {t('dividendYield')}
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)]">
                        {tickerData.fundamental.dividend_yield !== null
                          ? `${(tickerData.fundamental.dividend_yield * 100).toFixed(2)}%`
                          : t('notAvailable')}
                      </p>
                    </div>
                  </div>
                </Card>

                {/* EPS */}
                <Card padding="md">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-[var(--background)] p-2">
                      <Banknote className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                    <div>
                      <span className="text-xs text-[var(--foreground-muted)]">
                        {t('eps')}
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)]">
                        {tickerData.fundamental.eps !== null
                          ? `$${tickerData.fundamental.eps.toFixed(2)}`
                          : t('notAvailable')}
                      </p>
                    </div>
                  </div>
                </Card>

                {/* Sector */}
                <Card padding="md">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-[var(--background)] p-2">
                      <Building2 className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                    <div>
                      <span className="text-xs text-[var(--foreground-muted)]">
                        {t('sector')}
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)] truncate">
                        {tickerData.fundamental.sector || t('notAvailable')}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>
            </CollapsibleSection>
          )}

          {/* ===== Strategy Context ===== */}
          <CollapsibleSection
            title={t('strategyContext')}
            expanded={expandedSections.strategy}
            onToggle={() => toggleSection('strategy')}
            isPopup={isPopup}
            headerRight={
              presets.length > 0 ? (
                <select
                  value={selectedPreset}
                  onChange={(e) => {
                    setSelectedPreset(e.target.value);
                    fetchScreening(e.target.value);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] text-[var(--foreground)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                >
                  {presets.map((p) => (
                    <option key={p.name} value={p.name}>
                      {(() => {
                        try {
                          return `${tScreening(`presetNames.${p.name}` as never)} (${p.conditions.length})`;
                        } catch {
                          return `${toTitleCaseFromKey(p.name)} (${p.conditions.length})`;
                        }
                      })()}
                    </option>
                  ))}
                </select>
              ) : undefined
            }
          >
            <Card padding="md">
              {screeningLoading && (
                <div className="flex items-center gap-3 py-4">
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-[var(--color-primary)] border-t-transparent" />
                  <span className="text-[var(--foreground-muted)]">{t('loadingConditions')}</span>
                </div>
              )}

              {screeningError && !screeningLoading && (
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400 py-2">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">{screeningError}</span>
                </div>
              )}

              {screeningResult && !screeningLoading && (
                <div className="space-y-3">
                  {/* Summary */}
                  <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
                    <div className="flex items-center gap-2">
                      {screeningResult.matched ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                      )}
                      <span className="font-medium text-[var(--foreground)]">
                        {t('conditionsPassed', {
                          passed: screeningResult.conditions.filter(c => c.matched).length,
                          total: screeningResult.conditions.length,
                        })}
                      </span>
                    </div>
                    <span
                      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
                        screeningResult.matched
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                      }`}
                    >
                      {screeningResult.matched ? t('pass') : t('fail')}
                    </span>
                  </div>

                  {/* Individual conditions */}
                  {screeningResult.conditions.length > 0 ? (
                    <div className="space-y-2">
                      {screeningResult.conditions.map((condition, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-2 px-3 rounded-lg bg-[var(--background)] hover:bg-[var(--background-secondary)] transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            {getConditionIcon(condition)}
                            <span className="text-sm text-[var(--foreground)]">
                              {(() => {
                                try {
                                  return tConditions(`${condition.condition_name}.label` as never);
                                } catch {
                                  return toTitleCaseFromKey(condition.condition_name);
                                }
                              })()}
                            </span>
                          </div>
                          {getConditionBadge(condition)}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-[var(--foreground-muted)] py-2">
                      {t('noConditions')}
                    </p>
                  )}
                </div>
              )}
            </Card>
          </CollapsibleSection>

          {/* ===== AI Insight ===== */}
          <CollapsibleSection
            title={t('aiInsight')}
            expanded={expandedSections.ai}
            onToggle={() => toggleSection('ai')}
            isPopup={isPopup}
          >
            <Card padding="md">
              {aiAvailable === false && (
                <div className="flex items-center gap-3 py-4">
                  <ShieldAlert className="h-5 w-5 text-[var(--foreground-muted)]" />
                  <span className="text-sm text-[var(--foreground-muted)]">
                    {t('apiKeyMissing')}
                  </span>
                </div>
              )}

              {aiAvailable !== false && !aiResult && (
                <div className="flex flex-col items-center gap-4 py-6">
                  <Brain className="h-10 w-10 text-[var(--foreground-muted)]" />
                  <p className="text-sm text-[var(--foreground-muted)] text-center">
                    {t('aiDescription')}
                  </p>
                  <Button
                    variant="primary"
                    size="md"
                    onClick={handleAIAnalysis}
                    isLoading={aiLoading}
                    disabled={aiLoading}
                  >
                    {aiLoading ? (
                      t('analyzing')
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4 mr-2" />
                        {t('analyzeWithAI')}
                      </>
                    )}
                  </Button>
                  {aiError && (
                    <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="text-sm">{aiError}</span>
                    </div>
                  )}
                </div>
              )}

              {aiResult && (
                <div className="space-y-5">
                  {/* Scores row */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {/* Valuation Score */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-[var(--foreground-muted)]">
                          {t('valuationScore')}
                        </span>
                        <span className={`text-lg font-bold ${getScoreColor(aiResult.valuation_score)}`}>
                          {aiResult.valuation_score.toFixed(1)}/10
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--background)] overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${getScoreBarColor(aiResult.valuation_score)}`}
                          style={{ width: `${(aiResult.valuation_score / 10) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Risk Score */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-[var(--foreground-muted)]">
                          {t('riskScore')}
                        </span>
                        <span className={`text-lg font-bold ${getScoreColor(aiResult.risk_score, true)}`}>
                          {aiResult.risk_score.toFixed(1)}/10
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--background)] overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${getScoreBarColor(aiResult.risk_score, true)}`}
                          style={{ width: `${(aiResult.risk_score / 10) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Recommendation */}
                    <div className="flex flex-col items-center justify-center">
                      <span className="text-sm text-[var(--foreground-muted)] mb-2">
                        {t('recommendation')}
                      </span>
                      <span
                        className={`inline-flex items-center rounded-full px-4 py-2 text-lg font-bold ${getRecommendationStyle(aiResult.entry_recommendation)}`}
                      >
                        {getRecommendationLabel(aiResult.entry_recommendation)}
                      </span>
                    </div>
                  </div>

                  {/* Key Risks & Catalysts */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Key Risks */}
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-[var(--foreground-muted)]">
                        {t('keyRisks')}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {aiResult.key_risks.map((risk, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300"
                          >
                            {risk}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Catalysts */}
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-[var(--foreground-muted)]">
                        {t('catalysts')}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {aiResult.catalysts.map((catalyst, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center rounded-full px-3 py-1 text-xs font-medium bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
                          >
                            {catalyst}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Reasoning (collapsible) */}
                  <div className="border-t border-[var(--border)] pt-4">
                    <button
                      type="button"
                      onClick={() => setReasoningExpanded(!reasoningExpanded)}
                      className="flex items-center gap-2 text-sm font-medium text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors w-full"
                    >
                      {reasoningExpanded ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                      {t('reasoning')}
                    </button>
                    {reasoningExpanded && (
                      <div className="mt-3 p-4 rounded-lg bg-[var(--background)] text-sm text-[var(--foreground)] leading-relaxed whitespace-pre-wrap">
                        {aiResult.reasoning}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>
          </CollapsibleSection>

          {/* ===== Sector Distribution ===== */}
          {tickerData.fundamental?.sector && (
            <CollapsibleSection
              title={t('sectorDistribution')}
              expanded={expandedSections.sector}
              onToggle={() => toggleSection('sector')}
              isPopup={isPopup}
            >
              <Card padding="md">
                <div className="flex items-center gap-3">
                  <Building2 className="h-5 w-5 text-[var(--color-primary)]" />
                  <span
                    className="inline-flex items-center rounded-full px-4 py-2 text-sm font-medium bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                  >
                    {tickerData.fundamental.sector}
                  </span>
                </div>
              </Card>
            </CollapsibleSection>
          )}

          {/* ===== Price Summary & Trading Range ===== */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Price Summary */}
            <Card title={t('priceSummary')}>
              <div className="space-y-3">
                {tickerData.ohlcv.length > 0 && (() => {
                  const prices = tickerData.ohlcv.map(d => d.close);
                  const highs = tickerData.ohlcv.map(d => d.high);
                  const lows = tickerData.ohlcv.map(d => d.low);
                  const periodHigh = Math.max(...highs);
                  const periodLow = Math.min(...lows);
                  const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;
                  const firstPrice = prices[0];
                  const lastPrice = prices[prices.length - 1];
                  const periodReturn = ((lastPrice - firstPrice) / firstPrice) * 100;

                  return (
                    <>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--foreground-muted)]">{t('periodHigh')}</span>
                        <span className="font-medium text-[var(--foreground)]">
                          ${periodHigh.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--foreground-muted)]">{t('periodLow')}</span>
                        <span className="font-medium text-[var(--foreground)]">
                          ${periodLow.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--foreground-muted)]">{t('averagePrice')}</span>
                        <span className="font-medium text-[var(--foreground)]">
                          ${avgPrice.toFixed(2)}
                        </span>
                      </div>
                      <div className="h-px bg-[var(--border)]" />
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--foreground-muted)]">{t('periodReturn')}</span>
                        <span
                          className={`font-medium ${
                            periodReturn >= 0
                              ? 'text-green-600 dark:text-green-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {periodReturn >= 0 ? '+' : ''}{periodReturn.toFixed(2)}%
                        </span>
                      </div>
                    </>
                  );
                })()}
              </div>
            </Card>

            {/* Trading Range */}
            <Card title={t('tradingRange')}>
              <div className="space-y-4">
                {tickerData.ohlcv.length > 0 && (() => {
                  const highs = tickerData.ohlcv.map(d => d.high);
                  const lows = tickerData.ohlcv.map(d => d.low);
                  const periodHigh = Math.max(...highs);
                  const periodLow = Math.min(...lows);
                  const currentPrice = tickerData.current_price;
                  const range = periodHigh - periodLow;
                  const positionInRange = range > 0
                    ? ((currentPrice - periodLow) / range) * 100
                    : 50;

                  return (
                    <>
                      <div className="flex justify-between text-sm text-[var(--foreground-muted)]">
                        <span>{t('low')}: ${periodLow.toFixed(2)}</span>
                        <span>{t('high')}: ${periodHigh.toFixed(2)}</span>
                      </div>
                      <div className="relative h-3 rounded-full bg-gradient-to-r from-red-400 via-yellow-400 to-green-400">
                        <div
                          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-white border-2 border-[var(--color-primary)] shadow-md"
                          style={{ left: `calc(${Math.min(100, Math.max(0, positionInRange))}% - 8px)` }}
                        />
                      </div>
                      <div className="text-center">
                        <span className="text-sm text-[var(--foreground-muted)]">
                          {t('currentPriceAt')}{' '}
                        </span>
                        <span className="font-medium text-[var(--foreground)]">
                          {positionInRange.toFixed(0)}%
                        </span>
                        <span className="text-sm text-[var(--foreground-muted)]">
                          {' '}{t('ofRange')}
                        </span>
                      </div>
                    </>
                  );
                })()}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
