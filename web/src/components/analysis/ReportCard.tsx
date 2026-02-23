'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useLocale } from 'next-intl';
import { Link } from '@/i18n/navigation';
import {
  FileText,
  Calendar,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import type { ReportSummary, ReportDetail } from '@/lib/types';
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
  const t = useTranslations('reports');
  const tMarkets = useTranslations('markets');
  const locale = useLocale();
  const [isExpanded, setIsExpanded] = useState(false);
  const [detailData, setDetailData] = useState<ReportDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatDate = (dateStr: string) => {
    try {
      // Handle YYYYMMDD format
      const year = dateStr.slice(0, 4);
      const month = dateStr.slice(4, 6);
      const day = dateStr.slice(6, 8);
      const date = new Date(`${year}-${month}-${day}`);
      return new Intl.DateTimeFormat(locale, {
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
    const key = market.toLowerCase().replace(/[^a-z0-9]/g, '');
    try {
      return tMarkets(key);
    } catch {
      return market.toUpperCase();
    }
  };

  const handleToggle = async () => {
    if (!isExpanded && !detailData) {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getReportDetail(report.date);
        setDetailData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load details');
      } finally {
        setIsLoading(false);
      }
    }
    setIsExpanded(!isExpanded);
  };

  // Get a text preview from markdown content
  const getContentPreview = (content: string, maxLength: number = 200): string => {
    // Strip markdown headers and formatting
    const stripped = content
      .replace(/^#+\s+.*/gm, '') // headers
      .replace(/\*\*([^*]+)\*\*/g, '$1') // bold
      .replace(/\*([^*]+)\*/g, '$1') // italic
      .replace(/\|[^|]*\|/g, '') // table cells
      .replace(/[-=]{3,}/g, '') // horizontal rules
      .replace(/\n{2,}/g, '\n')
      .trim();

    if (stripped.length <= maxLength) return stripped;
    return stripped.slice(0, maxLength).trim() + '...';
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
            {report.buy_count > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                <TrendingUp className="h-3 w-3" />
                {report.buy_count} {t('buy')}
              </span>
            )}
            {report.total_stocks > 0 && (
              <span className="text-xs text-[var(--foreground-muted)]">
                ({report.total_stocks} {t('stocksUnit')})
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
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-[var(--background)] p-3">
                  <span className="text-xs text-[var(--foreground-muted)]">
                    {t('totalStocks')}
                  </span>
                  <p className="text-lg font-semibold text-[var(--foreground)]">
                    {report.total_stocks.toLocaleString()}
                  </p>
                </div>
                <div className="rounded-lg bg-[var(--background)] p-3">
                  <span className="text-xs text-[var(--foreground-muted)]">
                    {t('buySignals')}
                  </span>
                  <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                    {report.buy_count}
                  </p>
                </div>
                <div className="rounded-lg bg-[var(--background)] p-3">
                  <span className="text-xs text-[var(--foreground-muted)]">
                    {t('stocksData')}
                  </span>
                  <p className="text-lg font-semibold text-[var(--foreground)]">
                    {detailData.stocks.length}
                  </p>
                </div>
              </div>

              {/* Content preview */}
              {detailData.content && (
                <div className="rounded-lg bg-[var(--background)] p-3">
                  <span className="text-xs text-[var(--foreground-muted)]">{t('preview')}</span>
                  <p className="mt-1 text-sm text-[var(--foreground)] line-clamp-3">
                    {getContentPreview(detailData.content)}
                  </p>
                </div>
              )}

              {/* View full report link */}
              <Link
                href={`/analysis/reports/${report.date}`}
                className="inline-flex items-center gap-2 rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
              >
                <ExternalLink className="h-4 w-4" />
                {t('viewFullReport')}
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
