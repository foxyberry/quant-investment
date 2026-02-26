'use client';

import { useState, useCallback, useEffect } from 'react';
import { Search, BarChart3, X, ArrowRight, Sparkles } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { Card, Button } from '@/components/ui';
import { CandleChart, IndicatorPanel } from '@/components/charts';
import { getTickerAnalysis, searchTickers } from '@/lib/api';
import type { TickerAnalysis } from '@/lib/types';

/**
 * Extracts a market badge label from a ticker symbol suffix.
 * E.g. "005930.KS" -> "KRX", "7203.T" -> "TSE", "AAPL" -> "US"
 */
function getMarketBadge(ticker: string): string {
  if (ticker.includes('.KS') || ticker.includes('.KQ')) return 'KRX';
  if (ticker.includes('.T')) return 'TSE';
  if (ticker.includes('.L')) return 'LSE';
  if (ticker.includes('.HK')) return 'HKEX';
  if (ticker.includes('.SS') || ticker.includes('.SZ')) return 'CN';
  return 'US';
}

/**
 * Main analysis page with ticker search, charts, and indicators.
 */
export default function AnalysisPage() {
  const t = useTranslations('analysis');

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<
    Array<{ ticker: string; name: string }>
  >([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [tickerData, setTickerData] = useState<TickerAnalysis | null>(null);
  const [isLoadingChart, setIsLoadingChart] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);

  // Debounced search
  useEffect(() => {
    if (searchQuery.length < 1) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    const timeoutId = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchTickers(searchQuery);
        setSearchResults(results.slice(0, 8));
        setShowResults(true);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handleSelectTicker = useCallback(async (ticker: string) => {
    setSelectedTicker(ticker);
    setSearchQuery('');
    setShowResults(false);
    setIsLoadingChart(true);
    setChartError(null);

    try {
      const data = await getTickerAnalysis(ticker);
      setTickerData(data);
    } catch (err) {
      setChartError(
        err instanceof Error ? err.message : 'Failed to load chart data'
      );
      setTickerData(null);
    } finally {
      setIsLoadingChart(false);
    }
  }, []);

  const handleClearTicker = () => {
    setSelectedTicker(null);
    setTickerData(null);
    setChartError(null);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">
          {t('title')}
        </h1>
        <p className="mt-1 text-sm text-[var(--foreground-muted)]">
          {t('subtitle')}
        </p>
      </div>

      {/* Search Section */}
      <Card padding="md">
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--foreground-muted)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => searchResults.length > 0 && setShowResults(true)}
                placeholder={t('searchPlaceholder')}
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] py-3.5 pl-12 pr-4 text-base text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/30 focus:border-[var(--color-primary)] transition-shadow"
              />
              {isSearching && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--color-primary)] border-t-transparent" />
                </div>
              )}
            </div>

            {selectedTicker && (
              <button
                type="button"
                onClick={handleClearTicker}
                className="flex items-center gap-2 rounded-lg bg-[var(--color-primary)] px-4 py-3.5 text-white hover:bg-[var(--color-primary-light)] transition-colors"
              >
                <span className="font-medium">{selectedTicker}</span>
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Search Results Dropdown */}
          {showResults && searchResults.length > 0 && (
            <div className="absolute z-10 mt-2 w-full rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-lg">
              <ul className="py-1">
                {searchResults.map((result) => (
                  <li key={result.ticker}>
                    <button
                      type="button"
                      onClick={() => handleSelectTicker(result.ticker)}
                      className="w-full flex items-center justify-between rounded-lg mx-2 my-0.5 px-3 py-2.5 hover:bg-[var(--background)] text-left transition-colors"
                      style={{ width: 'calc(100% - 1rem)' }}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-[var(--foreground)]">
                          {result.ticker}
                        </span>
                        <span className="rounded-md bg-[var(--color-primary)]/10 text-[var(--color-primary)] px-1.5 py-0.5 text-xs font-mono">
                          {getMarketBadge(result.ticker)}
                        </span>
                        <span className="text-sm text-[var(--foreground-muted)]">
                          {result.name}
                        </span>
                      </div>
                      <ArrowRight className="h-4 w-4 text-[var(--foreground-muted)]" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Quick ticker buttons */}
        <div className="mt-4">
          <span className="block text-sm font-medium text-[var(--foreground-muted)] mb-2">
            {t('popularLabel')}
          </span>
          <div className="flex flex-wrap gap-2">
            {['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA'].map((ticker) => (
              <button
                key={ticker}
                type="button"
                onClick={() => handleSelectTicker(ticker)}
                className={`rounded-full px-3 py-1 text-sm font-medium border transition-all ${
                  selectedTicker === ticker
                    ? 'bg-[var(--color-primary)] text-white border-[var(--color-primary)] shadow-[0_0_0_3px_var(--color-primary)]/20'
                    : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--color-primary)]/40 hover:bg-[var(--background)]'
                }`}
              >
                {ticker}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Chart Section */}
      {(selectedTicker || isLoadingChart) && (
        <div className="space-y-4">
          {/* Chart Header */}
          <div className="flex items-center justify-between rounded-xl bg-[var(--background-secondary)] border border-[var(--border)] p-4">
            <div className="flex items-center gap-3">
              <BarChart3 className="h-6 w-6 text-[var(--color-primary)]" />
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-bold text-[var(--foreground)]">
                    {tickerData?.name || selectedTicker}
                  </h2>
                  {selectedTicker && (
                    <span className="rounded-md bg-[var(--color-primary)]/10 text-[var(--color-primary)] px-2 py-0.5 text-sm font-mono">
                      {selectedTicker}
                    </span>
                  )}
                </div>
                {tickerData && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-2xl font-mono font-bold text-[var(--foreground)]">
                      ${tickerData.current_price.toFixed(2)}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-sm font-medium ${
                        tickerData.change_pct >= 0
                          ? 'bg-green-500/10 text-green-500'
                          : 'bg-red-500/10 text-red-500'
                      }`}
                    >
                      {tickerData.change_pct >= 0 ? '+' : ''}
                      {tickerData.change_pct.toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
            {selectedTicker && (
              <Link
                href={`/analysis/${selectedTicker}`}
                className="flex items-center gap-2 rounded-lg border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)]/10 px-4 py-2 font-medium transition-colors"
              >
                {t('fullAnalysis')}
                <ArrowRight className="h-4 w-4" />
              </Link>
            )}
          </div>

          {/* Loading state */}
          {isLoadingChart && (
            <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] h-[400px] flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-[var(--color-primary)] border-t-transparent" />
                <span className="text-[var(--foreground-muted)]">
                  {t('loadingChart')}
                </span>
              </div>
            </div>
          )}

          {/* Error state */}
          {chartError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-900 dark:bg-red-950">
              <p className="text-red-600 dark:text-red-400">{chartError}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => selectedTicker && handleSelectTicker(selectedTicker)}
              >
                {t('retry')}
              </Button>
            </div>
          )}

          {/* Chart */}
          {tickerData && !isLoadingChart && (
            <>
              <CandleChart
                data={tickerData.ohlcv}
                height={400}
                showVolume={true}
              />

              {/* Indicators */}
              <div>
                <h3 className="text-lg font-semibold text-[var(--foreground)] pb-3 border-b border-[var(--border)] mb-4">
                  {t('technicalIndicators')}
                </h3>
                <IndicatorPanel technicalData={tickerData.technical} currentPrice={tickerData.current_price} />
              </div>
            </>
          )}
        </div>
      )}

      {/* Empty state - 3 Guide Cards */}
      {!selectedTicker && !isLoadingChart && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-6 hover:border-[var(--color-primary)]/30 transition-colors">
            <Search className="h-8 w-8 text-[var(--color-primary)] mb-3" />
            <h3 className="text-base font-bold text-[var(--foreground)] mb-1">
              {t('guideSearchTitle')}
            </h3>
            <p className="text-sm text-[var(--foreground-muted)]">
              {t('guideSearchDesc')}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-6 hover:border-[var(--color-primary)]/30 transition-colors">
            <BarChart3 className="h-8 w-8 text-[var(--color-primary)] mb-3" />
            <h3 className="text-base font-bold text-[var(--foreground)] mb-1">
              {t('guideTechnicalTitle')}
            </h3>
            <p className="text-sm text-[var(--foreground-muted)]">
              {t('guideTechnicalDesc')}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-6 hover:border-[var(--color-primary)]/30 transition-colors">
            <Sparkles className="h-8 w-8 text-[var(--color-primary)] mb-3" />
            <h3 className="text-base font-bold text-[var(--foreground)] mb-1">
              {t('guideFullTitle')}
            </h3>
            <p className="text-sm text-[var(--foreground-muted)]">
              {t('guideFullDesc')}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
