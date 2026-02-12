'use client';

import { useState } from 'react';
import {
  FileText,
  Calendar,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Target,
} from 'lucide-react';
import type { ReportSummary, AnalysisReport } from '@/lib/types';
import { getReportDetail } from '@/lib/api';

interface ReportCardProps {
  /** Report summary data */
  report: ReportSummary;
  /** Additional CSS class */
  className?: string;
}

/**
 * Displays a single analysis report summary with expandable details
 */
export default function ReportCard({ report, className = '' }: ReportCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [detailData, setDetailData] = useState<AnalysisReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return new Intl.DateTimeFormat('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(date);
    } catch {
      return dateStr;
    }
  };

  const getMarketLabel = (market: string) => {
    const marketLabels: Record<string, string> = {
      us: 'US Market',
      kr: 'Korea Market',
      kospi: 'KOSPI',
      kosdaq: 'KOSDAQ',
      nasdaq: 'NASDAQ',
      sp500: 'S&P 500',
    };
    return marketLabels[market.toLowerCase()] || market.toUpperCase();
  };

  const handleToggle = async () => {
    if (!isExpanded && !detailData) {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getReportDetail(report.filename);
        setDetailData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load details');
      } finally {
        setIsLoading(false);
      }
    }
    setIsExpanded(!isExpanded);
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'BUY':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'WAIT':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'AVOID':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div
      className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] overflow-hidden ${className}`}
    >
      {/* Header - Clickable */}
      <button
        type="button"
        onClick={handleToggle}
        className="w-full flex items-center gap-4 p-4 hover:bg-[var(--background)] transition-colors text-left"
      >
        {/* Report icon */}
        <div className="flex-shrink-0 rounded-lg bg-[var(--background)] p-3">
          <FileText className="h-6 w-6 text-[var(--color-primary)]" />
        </div>

        {/* Report info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-[var(--foreground)]">
              {getMarketLabel(report.market)}
            </span>
            {report.buy_count !== undefined && report.buy_count > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                <TrendingUp className="h-3 w-3" />
                {report.buy_count} BUY
              </span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-1 text-sm text-[var(--foreground-muted)]">
            <Calendar className="h-3.5 w-3.5" />
            <span>{formatDate(report.date)}</span>
          </div>
        </div>

        {/* Expand icon */}
        <div className="flex-shrink-0 text-[var(--foreground-muted)]">
          {isExpanded ? (
            <ChevronUp className="h-5 w-5" />
          ) : (
            <ChevronDown className="h-5 w-5" />
          )}
        </div>
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div className="border-t border-[var(--border)] p-4">
          {isLoading && (
            <div className="flex items-center justify-center py-6">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent" />
            </div>
          )}

          {error && (
            <div className="text-center py-4 text-red-600 dark:text-red-400">
              <p>{error}</p>
            </div>
          )}

          {detailData && !isLoading && (
            <div className="space-y-4">
              {/* Summary stats */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="rounded-lg bg-[var(--background)] p-3">
                  <span className="text-xs text-[var(--foreground-muted)]">
                    Total Screened
                  </span>
                  <p className="text-lg font-semibold text-[var(--foreground)]">
                    {detailData.total_screened.toLocaleString()}
                  </p>
                </div>
                <div className="rounded-lg bg-[var(--background)] p-3">
                  <span className="text-xs text-[var(--foreground-muted)]">
                    Matched
                  </span>
                  <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                    {detailData.matched_count.toLocaleString()}
                  </p>
                </div>
                <div className="rounded-lg bg-[var(--background)] p-3 col-span-2 sm:col-span-1">
                  <span className="text-xs text-[var(--foreground-muted)]">
                    Match Rate
                  </span>
                  <p className="text-lg font-semibold text-[var(--foreground)]">
                    {detailData.total_screened > 0
                      ? ((detailData.matched_count / detailData.total_screened) * 100).toFixed(1)
                      : 0}
                    %
                  </p>
                </div>
              </div>

              {/* Summary text */}
              {detailData.summary && (
                <div className="rounded-lg bg-[var(--background)] p-3">
                  <span className="text-xs text-[var(--foreground-muted)]">Summary</span>
                  <p className="mt-1 text-sm text-[var(--foreground)]">
                    {detailData.summary}
                  </p>
                </div>
              )}

              {/* Recommendations */}
              {detailData.recommendations && detailData.recommendations.length > 0 && (
                <div>
                  <h4 className="flex items-center gap-2 text-sm font-medium text-[var(--foreground)] mb-2">
                    <Target className="h-4 w-4" />
                    Recommendations ({detailData.recommendations.length})
                  </h4>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {detailData.recommendations.map((rec, index) => (
                      <div
                        key={`${rec.ticker}-${index}`}
                        className="flex items-center justify-between gap-3 rounded-lg bg-[var(--background)] p-3"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-[var(--foreground)]">
                              {rec.ticker}
                            </span>
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${getActionColor(
                                rec.action
                              )}`}
                            >
                              {rec.action}
                            </span>
                          </div>
                          <p className="text-sm text-[var(--foreground-muted)] truncate">
                            {rec.name}
                          </p>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-sm font-medium text-[var(--foreground)]">
                            Score: {rec.score}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
