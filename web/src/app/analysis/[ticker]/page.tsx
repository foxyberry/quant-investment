'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
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
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { CandleChart, IndicatorPanel } from '@/components/charts';
import { getTickerAnalysis } from '@/lib/api';
import type { TickerAnalysis } from '@/lib/types';

type PeriodOption = '1mo' | '3mo' | '6mo' | '1y' | '2y';

const periodOptions: { value: PeriodOption; label: string }[] = [
  { value: '1mo', label: '1 Month' },
  { value: '3mo', label: '3 Months' },
  { value: '6mo', label: '6 Months' },
  { value: '1y', label: '1 Year' },
  { value: '2y', label: '2 Years' },
];

/**
 * Dynamic ticker analysis page with full chart and indicators
 */
export default function TickerAnalysisPage() {
  const params = useParams();
  const ticker = params.ticker as string;

  const [tickerData, setTickerData] = useState<TickerAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodOption>('6mo');

  const fetchData = useCallback(async (period: PeriodOption) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getTickerAnalysis(ticker.toUpperCase(), period);
      setTickerData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      setTickerData(null);
    } finally {
      setIsLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    if (ticker) {
      fetchData(selectedPeriod);
    }
  }, [ticker, selectedPeriod, fetchData]);

  const handlePeriodChange = (period: PeriodOption) => {
    setSelectedPeriod(period);
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

  return (
    <div className="space-y-6">
      {/* Back navigation */}
      <Link
        href="/analysis"
        className="inline-flex items-center gap-2 text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Analysis
      </Link>

      {/* Header */}
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

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-4">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] h-[500px] flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="animate-spin rounded-full h-10 w-10 border-3 border-[var(--color-primary)] border-t-transparent" />
              <span className="text-[var(--foreground-muted)]">
                Loading {ticker.toUpperCase()} data...
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
              Failed to Load Data
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
              Retry
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
              Period:
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
            height={500}
            showVolume={true}
          />

          {/* Technical Indicators */}
          <div>
            <h2 className="text-xl font-semibold text-[var(--foreground)] mb-4">
              Technical Indicators
            </h2>
            <IndicatorPanel technicalData={tickerData.technical} />
          </div>

          {/* Fundamental Data */}
          {tickerData.fundamental && (
            <div>
              <h2 className="text-xl font-semibold text-[var(--foreground)] mb-4">
                Fundamental Data
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Market Cap */}
                <Card padding="md">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-[var(--background)] p-2">
                      <DollarSign className="h-5 w-5 text-[var(--color-primary)]" />
                    </div>
                    <div>
                      <span className="text-xs text-[var(--foreground-muted)]">
                        Market Cap
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
                        P/E Ratio
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)]">
                        {tickerData.fundamental.pe_ratio !== null
                          ? tickerData.fundamental.pe_ratio.toFixed(2)
                          : 'N/A'}
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
                        Dividend Yield
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)]">
                        {tickerData.fundamental.dividend_yield !== null
                          ? `${(tickerData.fundamental.dividend_yield * 100).toFixed(2)}%`
                          : 'N/A'}
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
                        Sector
                      </span>
                      <p className="text-lg font-semibold text-[var(--foreground)] truncate">
                        {tickerData.fundamental.sector || 'N/A'}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* Additional Analysis Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Price Summary */}
            <Card title="Price Summary">
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
                        <span className="text-[var(--foreground-muted)]">Period High</span>
                        <span className="font-medium text-[var(--foreground)]">
                          ${periodHigh.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--foreground-muted)]">Period Low</span>
                        <span className="font-medium text-[var(--foreground)]">
                          ${periodLow.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--foreground-muted)]">Average Price</span>
                        <span className="font-medium text-[var(--foreground)]">
                          ${avgPrice.toFixed(2)}
                        </span>
                      </div>
                      <div className="h-px bg-[var(--border)]" />
                      <div className="flex justify-between items-center">
                        <span className="text-[var(--foreground-muted)]">Period Return</span>
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
            <Card title="Trading Range">
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
                        <span>Low: ${periodLow.toFixed(2)}</span>
                        <span>High: ${periodHigh.toFixed(2)}</span>
                      </div>
                      <div className="relative h-3 rounded-full bg-gradient-to-r from-red-400 via-yellow-400 to-green-400">
                        <div
                          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-white border-2 border-[var(--color-primary)] shadow-md"
                          style={{ left: `calc(${Math.min(100, Math.max(0, positionInRange))}% - 8px)` }}
                        />
                      </div>
                      <div className="text-center">
                        <span className="text-sm text-[var(--foreground-muted)]">
                          Current price is at{' '}
                        </span>
                        <span className="font-medium text-[var(--foreground)]">
                          {positionInRange.toFixed(0)}%
                        </span>
                        <span className="text-sm text-[var(--foreground-muted)]">
                          {' '}of the {selectedPeriod} range
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
