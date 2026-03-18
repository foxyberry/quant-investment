'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { routing } from '@/i18n/routing';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Building2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Brain,
  ShieldAlert,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Star,
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { CandleChart, IndicatorPanel } from '@/components/charts';
import { FactorScoreBar, FundamentalCard, NewsCard } from '@/components/analysis';
import {
  getTickerAnalysis,
  analyzeStock,
  checkStockConditions,
  getAnalysisStatus,
  getPresets,
  createWatchlistItem,
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
    .replace(/^screening\.presetNames\./, '')
    .replace(/^conditions\./, '')
    .replace(/^custom:/, '')
    .replace(/_/g, ' ')
    .replace(/\./g, ' ')
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
  const tCompany = useTranslations('companyInfo');

  // Core data
  const [tickerData, setTickerData] = useState<TickerAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodOption>('6mo');

  // News (opt-in)
  const [newsLoading, setNewsLoading] = useState(false);
  const [newsLoaded, setNewsLoaded] = useState(false);
  const [newsError, setNewsError] = useState<string | null>(null);

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
  const [watchlistAdded, setWatchlistAdded] = useState(false);

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

  useEffect(() => {
    getPresets()
      .then(setPresets)
      .catch(() => {});
  }, []);

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
  // eslint-disable-next-line react-hooks/exhaustive-deps -- selectedPreset is read as fallback only
  }, [ticker, t]);

  useEffect(() => {
    getAnalysisStatus()
      .then((status) => setAiAvailable(status.ai_available ?? status.claude_available))
      .catch(() => setAiAvailable(false));
  }, []);

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

  useEffect(() => {
    if (ticker) fetchData(selectedPeriod);
  }, [ticker, selectedPeriod, fetchData]);

  useEffect(() => {
    if (ticker) fetchScreening();
  }, [ticker, fetchScreening]);

  const handlePeriodChange = (period: PeriodOption) => {
    setSelectedPeriod(period);
    setNewsError(null);
    setNewsLoaded(false);
  };

  const handleAIAnalysis = async () => {
    setAiLoading(true);
    setAiError(null);
    try {
      const result = await analyzeStock(ticker.toUpperCase(), true, locale);
      setAiResult(result);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : t('aiAnalysisError'));
    } finally {
      setAiLoading(false);
    }
  };

  const handleLoadNews = async () => {
    setNewsLoading(true);
    setNewsError(null);
    try {
      const data = await getTickerAnalysis(ticker.toUpperCase(), selectedPeriod, true);
      setTickerData(data);
      setNewsLoaded(true);
    } catch (err) {
      setNewsError(err instanceof Error ? err.message : 'error');
    } finally {
      setNewsLoading(false);
    }
  };

  // Currency symbol based on ticker exchange suffix
  const currencySymbol = ticker.toUpperCase().endsWith('.KS') || ticker.toUpperCase().endsWith('.KQ')
    ? '₩'
    : ticker.toUpperCase().endsWith('.T')
      ? '¥'
      : '$';

  const formatPrice = (value: number): string => {
    if (currencySymbol === '₩') return `₩ ${Math.round(value).toLocaleString()}`;
    if (currencySymbol === '¥') return `¥ ${Math.round(value).toLocaleString()}`;
    return `$ ${value.toFixed(2)}`;
  };

  const formatTimestamp = (ts: string): string => {
    const upper = ticker.toUpperCase();
    let closeH = 16, closeM = 0;
    if (upper.endsWith('.KS') || upper.endsWith('.KQ')) { closeH = 15; closeM = 30; }
    else if (upper.endsWith('.T')) { closeH = 15; }
    else if (upper.endsWith('.L')) { closeH = 16; closeM = 30; }
    else if (upper.endsWith('.SS') || upper.endsWith('.SZ')) { closeH = 15; }
    const midnight = new Date(ts);
    const closeDate = new Date(midnight.getTime() + closeH * 3600_000 + closeM * 60_000);
    return closeDate.toLocaleString(locale, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
      timeZoneName: 'short',
    });
  };

  const formatMarketCap = (value: number | null | undefined): string => {
    if (value == null) return '-';
    const sym = currencySymbol;
    if (value >= 1_000_000_000_000) return `${sym} ${(value / 1_000_000_000_000).toFixed(2)}T`;
    if (value >= 1_000_000_000) return `${sym} ${(value / 1_000_000_000).toFixed(2)}B`;
    if (value >= 1_000_000) return `${sym} ${(value / 1_000_000).toFixed(2)}M`;
    return `${sym} ${value.toLocaleString()}`;
  };

  const getConditionIcon = (condition: ConditionResult) => {
    return condition.matched
      ? <CheckCircle2 className="h-4 w-4 text-green-500" />
      : <XCircle className="h-4 w-4 text-red-500" />;
  };

  const getConditionBadge = (condition: ConditionResult) => {
    return condition.matched ? (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
        {t('pass')}
      </span>
    ) : (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
        {t('fail')}
      </span>
    );
  };

  const getRecommendationStyle = (rec: string) => {
    switch (rec) {
      case 'BUY': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'WAIT': return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200';
      case 'AVOID': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getRecommendationLabel = (rec: string) => {
    switch (rec) {
      case 'BUY': return t('recommendationBuy');
      case 'WAIT': return t('recommendationWait');
      case 'AVOID': return t('recommendationAvoid');
      default: return rec;
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
    indicators: true,
    financials: true,
    strategy: false,
    ai: false,
    companyInfo: false,
    news: true,
  });
  const [showAdvancedSections, setShowAdvancedSections] = useState(!isPopup);

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className={isPopup ? 'space-y-3' : 'space-y-6'}>
      {/* Popup header bar */}
      {isPopup && (
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 px-1 py-2 bg-[var(--background)] border-b border-[var(--border)]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-[var(--foreground)] truncate">
                  {tickerData?.name || ticker.toUpperCase()}
                </h1>
                <span className="shrink-0 rounded-md bg-[var(--color-primary)]/10 text-[var(--color-primary)] px-1.5 py-0.5 text-xs font-mono">
                  {ticker.toUpperCase()}
                </span>
              </div>
              {tickerData && (
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-lg font-semibold font-mono text-[var(--foreground)]">
                    {formatPrice(tickerData.current_price)}
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
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              aria-label={t('addToWatchlist')}
              onClick={async () => {
                try {
                  await createWatchlistItem({ ticker: ticker.toUpperCase(), name: tickerData?.name });
                } catch {
                  // 409 (already exists) or other — treat as success feedback
                }
                setWatchlistAdded(true);
                setTimeout(() => setWatchlistAdded(false), 3000);
              }}
              title={t('addToWatchlist')}
            >
              <Star className={`h-3.5 w-3.5 ${watchlistAdded ? 'fill-yellow-400 text-yellow-400' : ''}`} />
            </Button>
            <Button variant="outline" size="sm" onClick={() => fetchData(selectedPeriod)}>
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <a
              href={`/${locale}/analysis/${encodeURIComponent(ticker)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--background-secondary)] px-2 py-1.5 text-xs text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              {t('openFullPage')}
            </a>
          </div>
        </div>
      )}

      {/* Back navigation (full page only) */}
      {!isPopup && (
        <Link
          href="/analysis"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('backToAnalysis')}
        </Link>
      )}

      {/* ── HEADER ── */}
      {!isPopup && tickerData && (
        <div className="flex items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-[var(--foreground)]">
                {ticker.toUpperCase()}
              </h1>
              <span className="text-lg text-[var(--foreground-muted)]">{tickerData.name}</span>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-2xl font-semibold font-mono text-[var(--foreground)]">
                {formatPrice(tickerData.current_price)}
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold ${
                  tickerData.change_pct >= 0
                    ? 'bg-green-500/15 text-green-500'
                    : 'bg-red-500/15 text-red-500'
                }`}
              >
                {tickerData.change_pct >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                {tickerData.change_pct >= 0 ? '+' : ''}{tickerData.change_pct.toFixed(2)}%
              </span>
            </div>
            {tickerData.timestamp && (
              <p className="text-xs text-[var(--foreground-muted)] mt-1">
                {t('dataAsOf', { date: formatTimestamp(tickerData.timestamp) })}
                {' · '}{t('dataDelayNote')}
              </p>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={() => fetchData(selectedPeriod)}>
            <RefreshCw className="h-4 w-4 mr-1" />
            {t('refresh')}
          </Button>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="animate-spin h-10 w-10 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
          <p className="mt-4 text-[var(--foreground-muted)]">{t('loadingData', { ticker: ticker.toUpperCase() })}</p>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <Card className="text-center py-12">
          <p className="text-red-500 text-lg font-semibold mb-2">{t('loadFailed')}</p>
          <p className="text-[var(--foreground-muted)] mb-4">{error}</p>
          <Button onClick={() => fetchData(selectedPeriod)}>{t('retry')}</Button>
        </Card>
      )}

      {/* ── MAIN CONTENT ── */}
      {tickerData && !isLoading && !error && (
        <>
          {/* ── 5-FACTOR SCORE BAR ── */}
          <FactorScoreBar tickerData={tickerData} />

          {/* ── CHART SECTION ── */}
          <div>
            {/* Period selector */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex gap-1">
                {periodOptions.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => handlePeriodChange(opt.value)}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      selectedPeriod === opt.value
                        ? 'bg-[var(--color-primary)] text-white'
                        : 'bg-[var(--background-secondary)] text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {isPopup && (
                <Button variant="outline" size="sm" onClick={() => fetchData(selectedPeriod)}>
                  <RefreshCw className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>

            {/* Chart */}
            {tickerData.ohlcv.length > 0 ? (
              <CandleChart
                data={tickerData.ohlcv}
                height={isPopup ? 340 : 500}
                showVolume
              />
            ) : (
              <Card className="flex items-center justify-center py-16">
                <p className="text-[var(--foreground-muted)]">{t('noChartData')}</p>
              </Card>
            )}

            {/* OHLC strip */}
            {tickerData.ohlcv.length > 0 && (() => {
              const lastCandle = tickerData.ohlcv[tickerData.ohlcv.length - 1];
              return (
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-3">
                  {[
                    { label: t('open'), value: formatPrice(lastCandle.open) },
                    { label: t('high'), value: formatPrice(lastCandle.high) },
                    { label: t('low'), value: formatPrice(lastCandle.low) },
                    { label: t('close'), value: formatPrice(lastCandle.close) },
                    { label: t('ohlcvVol'), value: lastCandle.volume ? `${(lastCandle.volume / 1_000_000).toFixed(1)}M` : '-' },
                    ...(tickerData.technical.sma ? [
                      { label: t('ohlcvMa', { period: '20' }), value: formatPrice(tickerData.technical.sma.sma20) },
                    ] : []),
                  ].map((item) => (
                    <div key={item.label} className="rounded-md bg-[var(--background-secondary)] border border-[var(--border)] px-3 py-2 text-center">
                      <span className="block text-[10px] text-[var(--foreground-muted)]">{item.label}</span>
                      <span className="text-sm font-mono font-semibold text-[var(--foreground)]">{item.value}</span>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Popup: Show Advanced Details toggle */}
          {isPopup && (
            <button
              onClick={() => setShowAdvancedSections(!showAdvancedSections)}
              className="flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline mx-auto"
            >
              {showAdvancedSections ? t('hideAdvancedDetails') : t('showAdvancedDetails')}
              {showAdvancedSections ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          )}

          {/* ── BOTTOM DASHBOARD (2-column grid) ── */}
          {showAdvancedSections && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* ── LEFT COLUMN ── */}
              <div className="space-y-6">
                {/* Technical Indicators */}
                <CollapsibleSection
                  title={t('technicalIndicators')}
                  expanded={expandedSections.indicators}
                  onToggle={() => toggleSection('indicators')}
                  isPopup={isPopup}
                >
                  <IndicatorPanel
                    technicalData={tickerData.technical}
                    currentPrice={tickerData.current_price}
                  />
                </CollapsibleSection>

                {/* Fundamentals */}
                {tickerData.fundamental && (
                  <CollapsibleSection
                    title={t('fundamentalData')}
                    expanded={expandedSections.financials}
                    onToggle={() => toggleSection('financials')}
                    isPopup={isPopup}
                  >
                    <FundamentalCard fundamental={tickerData.fundamental} />

                    {/* 52-Week Range */}
                    {tickerData.fundamental.week52_high != null && tickerData.fundamental.week52_low != null && (
                      <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-4">
                        <h4 className="text-sm font-semibold text-[var(--foreground)] mb-3">{t('week52Range')}</h4>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-mono text-[var(--foreground-muted)]">
                            {formatPrice(tickerData.fundamental.week52_low)}
                          </span>
                          <div className="flex-1 relative h-2 rounded-full bg-[var(--border)]">
                            <div
                              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-[var(--color-primary)] border-2 border-white dark:border-gray-800 shadow"
                              style={{
                                left: `${Math.min(100, Math.max(0, ((tickerData.current_price - tickerData.fundamental.week52_low!) / (tickerData.fundamental.week52_high! - tickerData.fundamental.week52_low!)) * 100))}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs font-mono text-[var(--foreground-muted)]">
                            {formatPrice(tickerData.fundamental.week52_high)}
                          </span>
                        </div>
                      </div>
                    )}
                  </CollapsibleSection>
                )}

                {/* Strategy Context */}
                <CollapsibleSection
                  title={t('strategyContext')}
                  expanded={expandedSections.strategy}
                  onToggle={() => toggleSection('strategy')}
                  isPopup={isPopup}
                  headerRight={
                    screeningResult ? (
                      <span className="text-xs text-[var(--foreground-muted)]">
                        {t('conditionsPassed', {
                          passed: screeningResult.conditions.filter((c) => c.matched).length,
                          total: screeningResult.conditions.length,
                        })}
                      </span>
                    ) : undefined
                  }
                >
                  <div className="space-y-4">
                    {/* Preset selector */}
                    {presets.length > 0 && (
                      <select
                        value={selectedPreset}
                        onChange={(e) => {
                          setSelectedPreset(e.target.value);
                          fetchScreening(e.target.value);
                        }}
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--background-secondary)] text-[var(--foreground)] px-3 py-2 text-sm"
                      >
                        {presets.map((p) => (
                          <option key={p.name} value={p.name}>
                            {(() => {
                              try { return tScreening(`presetNames.${p.name}`); }
                              catch { return toTitleCaseFromKey(p.name); }
                            })()}
                          </option>
                        ))}
                      </select>
                    )}

                    {/* Conditions list */}
                    {screeningLoading && (
                      <p className="text-sm text-[var(--foreground-muted)]">{t('loadingConditions')}</p>
                    )}
                    {screeningError && (
                      <p className="text-sm text-red-500">{screeningError}</p>
                    )}
                    {screeningResult && !screeningLoading && (
                      <div className="space-y-2">
                        {screeningResult.conditions.map((cond) => (
                          <div key={cond.condition_name} className="flex items-center justify-between rounded-lg bg-[var(--background)]/60 border border-[var(--border)]/50 px-3 py-2">
                            <div className="flex items-center gap-2">
                              {getConditionIcon(cond)}
                              <span className="text-sm text-[var(--foreground)]">
                                {(() => {
                                  try { return tConditions(cond.condition_name); }
                                  catch { return toTitleCaseFromKey(cond.condition_name); }
                                })()}
                              </span>
                            </div>
                            {getConditionBadge(cond)}
                          </div>
                        ))}
                      </div>
                    )}
                    {!screeningResult && !screeningLoading && !screeningError && (
                      <p className="text-sm text-[var(--foreground-muted)]">{t('noConditions')}</p>
                    )}
                  </div>
                </CollapsibleSection>
              </div>

              {/* ── RIGHT COLUMN ── */}
              <div className="space-y-6">
                {/* Company Info */}
                {tickerData.fundamental && (
                  <CollapsibleSection
                    title={tCompany('title')}
                    expanded={expandedSections.companyInfo}
                    onToggle={() => toggleSection('companyInfo')}
                    isPopup={isPopup}
                  >
                    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-5 space-y-3">
                      <div className="flex gap-4">
                        {tickerData.fundamental.sector && (
                          <div>
                            <span className="text-xs text-[var(--foreground-muted)]">{tCompany('sector')}</span>
                            <p className="text-sm font-medium text-[var(--foreground)] flex items-center gap-1">
                              <Building2 className="h-3.5 w-3.5" />
                              {tickerData.fundamental.sector}
                            </p>
                          </div>
                        )}
                        {tickerData.fundamental.industry && (
                          <div>
                            <span className="text-xs text-[var(--foreground-muted)]">{tCompany('industry')}</span>
                            <p className="text-sm font-medium text-[var(--foreground)]">
                              {tickerData.fundamental.industry}
                            </p>
                          </div>
                        )}
                      </div>
                      {tickerData.fundamental.description && (
                        <p className="text-sm text-[var(--foreground-muted)] leading-relaxed line-clamp-4">
                          {tickerData.fundamental.description}
                        </p>
                      )}
                      {tickerData.fundamental.market_cap != null && (
                        <div className="pt-2 border-t border-[var(--border)]">
                          <span className="text-xs text-[var(--foreground-muted)]">{t('marketCap')}</span>
                          <p className="text-lg font-semibold font-mono text-[var(--color-primary)]">
                            {formatMarketCap(tickerData.fundamental.market_cap)}
                          </p>
                        </div>
                      )}
                    </div>
                  </CollapsibleSection>
                )}

                {/* News */}
                <CollapsibleSection
                  title="News"
                  expanded={expandedSections.news}
                  onToggle={() => toggleSection('news')}
                  isPopup={isPopup}
                >
                  <NewsCard
                    articles={tickerData.news?.articles}
                    sentimentSummary={tickerData.news?.sentiment_summary}
                    onLoadNews={!newsLoaded ? handleLoadNews : undefined}
                    isLoading={newsLoading}
                    error={newsError}
                    onRetry={handleLoadNews}
                  />
                </CollapsibleSection>

                {/* AI Insight */}
                <CollapsibleSection
                  title={t('aiInsight')}
                  expanded={expandedSections.ai}
                  onToggle={() => toggleSection('ai')}
                  isPopup={isPopup}
                >
                  <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-5 space-y-4">
                    <p className="text-xs text-[var(--foreground-muted)]">{t('aiDescription')}</p>

                    {!aiResult && aiAvailable && (
                      <Button
                        onClick={handleAIAnalysis}
                        isLoading={aiLoading}
                        variant="primary"
                        size="sm"
                      >
                        <Sparkles className="h-4 w-4 mr-1" />
                        {aiLoading ? t('analyzing') : t('analyzeWithAI')}
                      </Button>
                    )}

                    {!aiResult && aiAvailable === false && (
                      <p className="text-sm text-amber-500">{t('apiKeyMissing')}</p>
                    )}

                    {aiError && (
                      <p className="text-sm text-red-500">{aiError}</p>
                    )}

                    {aiResult && (
                      <div className="space-y-4">
                        {/* Recommendation badge */}
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex items-center gap-1 rounded-full px-4 py-1.5 text-sm font-bold ${getRecommendationStyle(aiResult.entry_recommendation)}`}>
                            {getRecommendationLabel(aiResult.entry_recommendation)}
                          </span>
                        </div>

                        {/* Score bars */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-[var(--foreground-muted)]">{t('valuationScore')}</span>
                              <span className={`text-sm font-bold ${getScoreColor(aiResult.valuation_score)}`}>
                                {aiResult.valuation_score}/10
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-[var(--border)] overflow-hidden">
                              <div className={`h-full rounded-full ${getScoreBarColor(aiResult.valuation_score)}`} style={{ width: `${aiResult.valuation_score * 10}%` }} />
                            </div>
                          </div>
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-[var(--foreground-muted)]">{t('riskScore')}</span>
                              <span className={`text-sm font-bold ${getScoreColor(aiResult.risk_score, true)}`}>
                                {aiResult.risk_score}/10
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-[var(--border)] overflow-hidden">
                              <div className={`h-full rounded-full ${getScoreBarColor(aiResult.risk_score, true)}`} style={{ width: `${aiResult.risk_score * 10}%` }} />
                            </div>
                          </div>
                        </div>

                        {/* Risks & Catalysts */}
                        {aiResult.key_risks.length > 0 && (
                          <div>
                            <h4 className="text-xs font-semibold text-[var(--foreground-muted)] mb-2 flex items-center gap-1">
                              <ShieldAlert className="h-3.5 w-3.5" />
                              {t('keyRisks')}
                            </h4>
                            <div className="flex flex-wrap gap-1.5">
                              {aiResult.key_risks.map((risk, i) => (
                                <span key={i} className="px-2 py-1 rounded-md text-xs bg-red-500/10 text-red-500">
                                  {risk}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {aiResult.catalysts.length > 0 && (
                          <div>
                            <h4 className="text-xs font-semibold text-[var(--foreground-muted)] mb-2 flex items-center gap-1">
                              <Brain className="h-3.5 w-3.5" />
                              {t('catalysts')}
                            </h4>
                            <div className="flex flex-wrap gap-1.5">
                              {aiResult.catalysts.map((c, i) => (
                                <span key={i} className="px-2 py-1 rounded-md text-xs bg-green-500/10 text-green-500">
                                  {c}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Reasoning */}
                        {aiResult.reasoning && (
                          <div>
                            <button
                              onClick={() => setReasoningExpanded(!reasoningExpanded)}
                              className="flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
                            >
                              {t('reasoning')}
                              {reasoningExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                            </button>
                            {reasoningExpanded && (
                              <p className="mt-2 text-sm text-[var(--foreground-muted)] leading-relaxed whitespace-pre-wrap">
                                {aiResult.reasoning}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </CollapsibleSection>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
