'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ArrowLeft,
  Calendar,
  BarChart3,
  TrendingUp,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useReportDetail } from '@/hooks';

interface ReportDetailPageProps {
  params: Promise<{ date: string }>;
}

export default function ReportDetailPage({ params }: ReportDetailPageProps) {
  const { date } = use(params);
  const { data: report, isLoading, error } = useReportDetail(date);
  const [activeTab, setActiveTab] = useState<'report' | 'stocks'>('report');

  const formatDate = (dateStr: string) => {
    try {
      const year = dateStr.slice(0, 4);
      const month = dateStr.slice(4, 6);
      const day = dateStr.slice(6, 8);
      const d = new Date(`${year}-${month}-${day}`);
      return new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      }).format(d);
    } catch {
      return dateStr;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-[var(--color-primary)]" />
          <p className="text-[var(--foreground-muted)]">Loading report...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="space-y-6">
        <Link
          href="/analysis"
          className="inline-flex items-center gap-2 text-sm text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Analysis
        </Link>

        <div className="flex flex-col items-center justify-center min-h-[300px] rounded-lg border border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950 p-8">
          <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
          <h2 className="text-xl font-semibold text-red-800 dark:text-red-200">
            Report Not Found
          </h2>
          <p className="mt-2 text-red-600 dark:text-red-400">
            {error instanceof Error
              ? error.message
              : `No report found for date: ${date}`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back navigation */}
      <Link
        href="/analysis"
        className="inline-flex items-center gap-2 text-sm text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Analysis
      </Link>

      {/* Header */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[var(--foreground)]">
              Analysis Report
            </h1>
            <div className="mt-2 flex items-center gap-4 text-sm text-[var(--foreground-muted)]">
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                {formatDate(date)}
              </span>
              <span className="flex items-center gap-1">
                <BarChart3 className="h-4 w-4" />
                {report.market}
              </span>
              {report.stocks.length > 0 && (
                <span className="flex items-center gap-1">
                  <TrendingUp className="h-4 w-4" />
                  {report.stocks.length} stocks analyzed
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      {report.stocks.length > 0 && (
        <div className="flex border-b border-[var(--border)]">
          <button
            type="button"
            onClick={() => setActiveTab('report')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'report'
                ? 'border-[var(--color-primary)] text-[var(--color-primary)]'
                : 'border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            Report
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('stocks')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'stocks'
                ? 'border-[var(--color-primary)] text-[var(--color-primary)]'
                : 'border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            Stocks ({report.stocks.length})
          </button>
        </div>
      )}

      {/* Report content */}
      {activeTab === 'report' && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-6 sm:p-8">
          <div className="prose prose-sm sm:prose-base max-w-none report-prose">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.content}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Stocks tab */}
      {activeTab === 'stocks' && report.stocks.length > 0 && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                  <th className="text-left p-3 font-medium text-[var(--foreground)]">
                    Ticker
                  </th>
                  <th className="text-left p-3 font-medium text-[var(--foreground)]">
                    Name
                  </th>
                  <th className="text-right p-3 font-medium text-[var(--foreground)]">
                    Price
                  </th>
                  <th className="text-left p-3 font-medium text-[var(--foreground)]">
                    Recommendation
                  </th>
                </tr>
              </thead>
              <tbody>
                {report.stocks.map((stock, index) => {
                  const ticker = String(stock.ticker || '');
                  const name = String(stock.name || '-');
                  const price = stock.current_price ? Number(stock.current_price) : null;
                  const rec = stock.entry_recommendation ? String(stock.entry_recommendation) : null;

                  return (
                    <tr
                      key={`${ticker || index}`}
                      className="border-b border-[var(--border)] last:border-b-0 hover:bg-[var(--background)] transition-colors"
                    >
                      <td className="p-3">
                        {ticker ? (
                          <Link
                            href={`/analysis/${ticker}`}
                            className="font-medium text-[var(--color-primary)] hover:underline"
                          >
                            {ticker}
                          </Link>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="p-3 text-[var(--foreground)]">{name}</td>
                      <td className="p-3 text-right text-[var(--foreground)]">
                        {price !== null
                          ? price.toLocaleString(undefined, {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })
                          : '-'}
                      </td>
                      <td className="p-3">
                        {rec && (
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                              rec === 'BUY'
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                : rec === 'AVOID'
                                  ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                  : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                            }`}
                          >
                            {rec}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
