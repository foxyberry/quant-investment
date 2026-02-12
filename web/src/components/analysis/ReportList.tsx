'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { FileText, Calendar, Filter, RefreshCw } from 'lucide-react';
import ReportCard from './ReportCard';
import { Button } from '@/components/ui';
import { getReports } from '@/lib/api';
import type { ReportSummary } from '@/lib/types';

interface ReportListProps {
  /** Initial number of reports to load */
  initialLimit?: number;
  /** Additional CSS class */
  className?: string;
}

/**
 * List of analysis reports with date filtering
 */
export default function ReportList({
  initialLimit = 10,
  className = '',
}: ReportListProps) {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateFilter, setDateFilter] = useState<string>('all');

  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getReports(initialLimit);
      setReports(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setIsLoading(false);
    }
  }, [initialLimit]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Filter reports by date
  const filteredReports = useMemo(() => {
    if (dateFilter === 'all') return reports;

    const now = new Date();
    const filterDate = new Date();

    switch (dateFilter) {
      case 'today':
        filterDate.setHours(0, 0, 0, 0);
        break;
      case 'week':
        filterDate.setDate(now.getDate() - 7);
        break;
      case 'month':
        filterDate.setMonth(now.getMonth() - 1);
        break;
      default:
        return reports;
    }

    return reports.filter((report) => {
      const reportDate = new Date(report.date);
      return reportDate >= filterDate;
    });
  }, [reports, dateFilter]);

  // Get unique dates for grouping
  const groupedReports = useMemo(() => {
    const groups: Record<string, ReportSummary[]> = {};

    filteredReports.forEach((report) => {
      const dateKey = report.date;
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(report);
    });

    return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a));
  }, [filteredReports]);

  const formatGroupDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const reportDate = new Date(dateStr);
      reportDate.setHours(0, 0, 0, 0);

      const diffDays = Math.floor(
        (today.getTime() - reportDate.getTime()) / (1000 * 60 * 60 * 24)
      );

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;

      return new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      }).format(date);
    } catch {
      return dateStr;
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="h-8 w-32 rounded bg-[var(--border)] animate-pulse" />
          <div className="h-10 w-40 rounded bg-[var(--border)] animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-24 rounded-lg bg-[var(--border)] animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950 ${className}`}>
        <div className="flex flex-col items-center text-center">
          <FileText className="h-10 w-10 text-red-500 mb-3" />
          <h3 className="text-lg font-medium text-red-800 dark:text-red-200">
            Failed to Load Reports
          </h3>
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={fetchReports}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // Empty state
  if (reports.length === 0) {
    return (
      <div className={`rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-8 ${className}`}>
        <div className="flex flex-col items-center text-center">
          <FileText className="h-12 w-12 text-[var(--foreground-muted)] mb-4" />
          <h3 className="text-lg font-medium text-[var(--foreground)]">
            No Reports Available
          </h3>
          <p className="mt-1 text-sm text-[var(--foreground-muted)]">
            Run a screening to generate analysis reports
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-[var(--foreground-muted)]" />
          <span className="text-sm text-[var(--foreground-muted)]">
            {filteredReports.length} report{filteredReports.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-[var(--foreground-muted)]" />
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-1.5 text-sm text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            <option value="all">All Time</option>
            <option value="today">Today</option>
            <option value="week">Last 7 Days</option>
            <option value="month">Last 30 Days</option>
          </select>
        </div>
      </div>

      {/* No results after filter */}
      {filteredReports.length === 0 && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-6 text-center">
          <p className="text-[var(--foreground-muted)]">
            No reports match the selected filter
          </p>
        </div>
      )}

      {/* Grouped reports */}
      {groupedReports.map(([date, dateReports]) => (
        <div key={date} className="space-y-3">
          <h3 className="text-sm font-medium text-[var(--foreground-muted)] flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            {formatGroupDate(date)}
          </h3>
          <div className="space-y-3">
            {dateReports.map((report, index) => (
              <ReportCard
                key={`${report.filename}-${index}`}
                report={report}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
