'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AlertCircle } from 'lucide-react';
import { ConditionMonitorPanel, FilterPanel, ResultTable } from '@/components/screening';
import { runScreening } from '@/lib/api';
import type { ScreeningResult } from '@/lib/types';

/**
 * Screening page for running stock screening presets
 */
export default function ScreeningPage() {
  const t = useTranslations('screening');
  const [activeMode, setActiveMode] = useState<'preset' | 'condition'>('preset');
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [selectedUniverse, setSelectedUniverse] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<ScreeningResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<{
    total: number;
    matched: number;
  } | null>(null);

  const handleRunScreening = async () => {
    if (!selectedPreset || !selectedUniverse) {
      setError(t('selectPresetAndUniverse'));
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults([]);
    setStats(null);

    try {
      const response = await runScreening(selectedPreset, selectedUniverse);
      setResults(response.results);
      setStats({
        total: response.total_count,
        matched: response.matched_count,
      });
    } catch (err) {
      console.error('Screening failed:', err);
      setError(
        err instanceof Error
          ? err.message
          : t('failedToRun')
      );
    } finally {
      setIsLoading(false);
    }
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
                selectedUniverse={selectedUniverse}
                isLoading={isLoading}
                onPresetChange={setSelectedPreset}
                onUniverseChange={setSelectedUniverse}
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

              {/* Stats Bar */}
              {stats && (
                <div className="flex flex-wrap items-center gap-4 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3">
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
                </div>
              )}

              {/* Results Table */}
              <ResultTable results={results} isLoading={isLoading} />
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
