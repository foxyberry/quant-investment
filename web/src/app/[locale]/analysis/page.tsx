'use client';

import { useState, useCallback, useEffect } from 'react';
import { Search, BarChart3, X, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { Card, Button } from '@/components/ui';
import { CandleChart, IndicatorPanel } from '@/components/charts';
import { getTickerAnalysis, searchTickers } from '@/lib/api';
import type { TickerAnalysis } from '@/lib/types';

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
        <p className="mt-1 text-[var(--foreground-muted)]">
          {t('subtitle')}
        </p>
      </div>

      {/* Search Section */}
      <Card padding="md">
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--foreground-muted)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => searchResults.length > 0 && setShowResults(true)}
                placeholder={t('searchPlaceholder')}
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] py-2.5 pl-10 pr-4 text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
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
                className="flex items-center gap-2 rounded-lg bg-[var(--color-primary)] px-4 py-2.5 text-white hover:bg-[var(--color-primary-light)] transition-colors"
              >
                <span className="font-medium">{selectedTicker}</span>
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Search Results Dropdown */}
          {showResults && searchResults.length > 0 && (
            <div className="absolute z-10 mt-2 w-full rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-lg">
              <ul className="py-2">
                {searchResults.map((result) => (
                  <li key={result.ticker}>
                    <button
                      type="button"
                      onClick={() => handleSelectTicker(result.ticker)}
                      className="w-full flex items-center justify-between px-4 py-2 hover:bg-[var(--background)] text-left transition-colors"
                    >
                      <div>
                        <span className="font-medium text-[var(--foreground)]">
                          {result.ticker}
                        </span>
                        <span className="ml-2 text-sm text-[var(--foreground-muted)]">
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
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-[var(--foreground-muted)] mr-2">
            {t('popular')}:
          </span>
          {['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA'].map((ticker) => (
            <button
              key={ticker}
              type="button"
              onClick={() => handleSelectTicker(ticker)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                selectedTicker === ticker
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--background)] text-[var(--foreground)] hover:bg-[var(--border)]'
              }`}
            >
              {ticker}
            </button>
          ))}
        </div>
      </Card>

      {/* Chart Section */}
      {(selectedTicker || isLoadingChart) && (
        <div className="space-y-4">
          {/* Chart Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <BarChart3 className="h-6 w-6 text-[var(--color-primary)]" />
              <div>
                <h2 className="text-xl font-semibold text-[var(--foreground)]">
                  {tickerData?.name || selectedTicker}
                </h2>
                {tickerData && (
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-lg font-medium text-[var(--foreground)]">
                      ${tickerData.current_price.toFixed(2)}
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        tickerData.change_pct >= 0
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
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
                className="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)] transition-colors"
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
                <h3 className="text-lg font-semibold text-[var(--foreground)] mb-3">
                  {t('technicalIndicators')}
                </h3>
                <IndicatorPanel technicalData={tickerData.technical} />
              </div>
            </>
          )}
        </div>
      )}

      {/* Empty state for chart */}
      {!selectedTicker && !isLoadingChart && (
        <Card padding="lg" className="text-center">
          <BarChart3 className="h-12 w-12 text-[var(--foreground-muted)] mx-auto mb-4" />
          <h3 className="text-lg font-medium text-[var(--foreground)]">
            {t('selectTicker')}
          </h3>
          <p className="mt-1 text-sm text-[var(--foreground-muted)]">
            {t('selectTickerDesc')}
          </p>
        </Card>
      )}
    </div>
  );
}
