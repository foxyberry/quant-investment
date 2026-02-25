'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AlertCircle, Clock } from 'lucide-react';
import { ConditionMonitorPanel, FilterPanel, ResultTable } from '@/components/screening';
import { runScreeningStream } from '@/lib/api';
import type { ScreeningProgressEvent, ScreeningResult } from '@/lib/types';

export default function ScreeningPage() {
  const t = useTranslations('screening');
  const [activeMode, setActiveMode] = useState<'preset' | 'condition'>('preset');
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [selectedUniverses, setSelectedUniverses] = useState<string[]>(['KOSPI']);
  const [referenceDate, setReferenceDate] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<ScreeningResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState(false);
  const [progress, setProgress] = useState<ScreeningProgressEvent | null>(null);
  const [stats, setStats] = useState<{
    total: number;
    matched: number;
    universes: string[];
    referenceDate: string | null;
    elapsedMs: number | null;
  } | null>(null);

  const handleRunScreening = async () => {
    if (!selectedPreset || selectedUniverses.length === 0) {
      setError(t('selectPresetAndUniverse'));
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults([]);
    setStats(null);
    setProgress({
      processed_tickers: 0,
      total_tickers: 0,
      matched_count: 0,
      progress_pct: 0,
      status: 'running',
    });

    runScreeningStream(selectedPreset, selectedUniverses, referenceDate, undefined, {
      onProgress: (event) => {
        setProgress(event);
        if (event.status === 'error') {
          setHasRun(true);
          setError(event.message || t('failedToRun'));
          setIsLoading(false);
        }
      },
      onResult: (response) => {
        setResults(response.results);
        setHasRun(true);
        setStats({
          total: response.total_count,
          matched: response.matched_count,
          universes: response.universes ?? selectedUniverses,
          referenceDate: response.reference_date ?? referenceDate,
          elapsedMs: response.elapsed_ms ?? null,
        });
        setProgress({
          processed_tickers: response.total_count,
          total_tickers: response.total_count,
          matched_count: response.matched_count,
          progress_pct: 100,
          status: 'done',
        });
        setIsLoading(false);
      },
      onError: (message) => {
        console.error('Screening failed:', message);
        setHasRun(true);
        setError(message || t('failedToRun'));
        setIsLoading(false);
        setProgress((prev) =>
          prev
            ? { ...prev, status: 'error', message }
            : {
                processed_tickers: 0,
                total_tickers: 0,
                matched_count: 0,
                progress_pct: 0,
                status: 'error',
                message,
              }
        );
      },
    });
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

      {/* Main Content Grid */}
      <div className="space-y-4">
        <div className="flex gap-1 rounded-lg bg-[var(--background)] p-1 w-fit">
          <button
            type="button"
            onClick={() => setActiveMode('preset')}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeMode === 'preset'
                ? 'bg-[var(--background-secondary)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {t('presetTab')}
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('condition')}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeMode === 'condition'
                ? 'bg-[var(--background-secondary)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {t('conditionTab')}
          </button>
        </div>

        {activeMode === 'preset' ? (
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            {/* Filter Panel - Sidebar on desktop */}
            <div className="lg:sticky lg:top-6 lg:self-start">
              <FilterPanel
                selectedPreset={selectedPreset}
                selectedUniverses={selectedUniverses}
                referenceDate={referenceDate}
                isLoading={isLoading}
                onPresetChange={setSelectedPreset}
                onUniverseChange={setSelectedUniverses}
                onReferenceDateChange={setReferenceDate}
                onRun={handleRunScreening}
              />
            </div>

            {/* Results Section */}
            <div className="space-y-4">
              {/* Error Message */}
              {error && (
                <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
                  <AlertCircle className="h-5 w-5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {progress && (
                <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-4">
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="text-[var(--foreground-muted)]">{t('runningScreening')}</span>
                    <span className="font-semibold text-[var(--foreground)]">
                      {progress.progress_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--background)]">
                    <div
                      className="h-full bg-[var(--color-primary)] transition-all duration-300"
                      style={{ width: `${Math.max(0, Math.min(100, progress.progress_pct))}%` }}
                    />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--foreground-muted)]">
                    <span>
                      {progress.processed_tickers.toLocaleString()} / {progress.total_tickers.toLocaleString()}
                    </span>
                    <span>matched: {progress.matched_count.toLocaleString()}</span>
                    <span>status: {progress.status}</span>
                  </div>
                </div>
              )}

              {/* Stats Bar */}
              {stats && (
                <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3">
                  {/* Universe badges */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {stats.universes.map((universe) => (
                      <span
                        key={universe}
                        className="inline-flex items-center rounded-full bg-[var(--color-primary)]/10 px-2.5 py-0.5 text-xs font-medium text-[var(--color-primary)]"
                      >
                        {universe}
                      </span>
                    ))}
                  </div>
                  {/* Reference date badge */}
                  <span className="inline-flex items-center rounded-full bg-[var(--background)] border border-[var(--border)] px-2.5 py-0.5 text-xs text-[var(--foreground-muted)]">
                    {stats.referenceDate ?? t('latestData')}
                  </span>
                  <div className="h-4 w-px bg-[var(--border)]" />
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-[var(--foreground-muted)]">
                      {t('totalScreened')}
                    </span>
                    <span className="font-semibold text-[var(--foreground)]">
                      {stats.total.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-4 w-px bg-[var(--border)]" />
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-[var(--foreground-muted)]">
                      {t('matched')}
                    </span>
                    <span className="font-semibold text-green-600 dark:text-green-400">
                      {stats.matched.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-4 w-px bg-[var(--border)]" />
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-[var(--foreground-muted)]">
                      {t('matchRate')}
                    </span>
                    <span className="font-semibold text-[var(--foreground)]">
                      {stats.total > 0
                        ? ((stats.matched / stats.total) * 100).toFixed(1)
                        : '0'}
                      %
                    </span>
                  </div>
                  {/* Execution time */}
                  {stats.elapsedMs != null && (
                    <>
                      <div className="h-4 w-px bg-[var(--border)]" />
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-[var(--foreground-muted)]" />
                        <span className="text-sm text-[var(--foreground-muted)]">
                          {t('executionTime')}
                        </span>
                        <span className="font-semibold text-[var(--foreground)]">
                          {stats.elapsedMs >= 1000
                            ? `${(stats.elapsedMs / 1000).toFixed(1)}s`
                            : `${Math.round(stats.elapsedMs)}ms`}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Results Table */}
              <ResultTable
                results={results}
                isLoading={isLoading}
                hasRun={hasRun}
                onRunScreening={handleRunScreening}
              />
            </div>
          </div>
        ) : (
          <div>
            <ConditionMonitorPanel />
          </div>
        )}
      </div>
    </div>
  );
}
