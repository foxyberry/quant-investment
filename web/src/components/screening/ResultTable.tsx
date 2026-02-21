'use client';

import { useState, useMemo, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { ChevronDown, ChevronUp, CheckCircle, XCircle, Search, ArrowUpDown } from 'lucide-react';
import type { ScreeningResult } from '@/lib/types';
import ConditionDetails from './ConditionDetails';

type SortField = 'ticker' | 'name' | 'current_price';
type SortDirection = 'asc' | 'desc';

interface ResultTableProps {
  /** Screening results to display */
  results: ScreeningResult[];
  /** Whether data is loading */
  isLoading?: boolean;
}

interface SortButtonProps {
  field: SortField;
  currentField: SortField;
  children: React.ReactNode;
  onSort: (field: SortField) => void;
}

/**
 * Sort button component for table headers
 */
function SortButton({ field, currentField, children, onSort }: SortButtonProps) {
  return (
    <button
      type="button"
      onClick={() => onSort(field)}
      className="flex items-center gap-1 font-semibold text-[var(--foreground)] hover:text-[var(--color-primary)] transition-colors"
    >
      {children}
      <ArrowUpDown
        className={`h-4 w-4 ${
          currentField === field
            ? 'text-[var(--color-primary)]'
            : 'text-[var(--foreground-muted)]'
        }`}
      />
    </button>
  );
}

/**
 * Format a price value for display
 */
function formatPrice(price: number | null): string {
  if (price === null) return '-';
  return price.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Table displaying screening results with expandable rows for condition details
 */
export default function ResultTable({ results, isLoading }: ResultTableProps) {
  const t = useTranslations('screening');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('ticker');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const sortedResults = useMemo(() => {
    return [...results].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'ticker':
          comparison = a.ticker.localeCompare(b.ticker);
          break;
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'current_price': {
          const priceA = a.current_price ?? 0;
          const priceB = b.current_price ?? 0;
          comparison = priceA - priceB;
          break;
        }
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [results, sortField, sortDirection]);

  const handleSort = useCallback((field: SortField) => {
    setSortField((prevField) => {
      if (prevField === field) {
        setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
        return prevField;
      }
      setSortDirection('asc');
      return field;
    });
  }, []);

  const toggleRow = useCallback((ticker: string) => {
    setExpandedRow((prev) => (prev === ticker ? null : ticker));
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]">
        <div className="flex h-64 flex-col items-center justify-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--color-primary)]" />
          <p className="text-[var(--foreground-muted)]">
            {t('runningScreening')}
          </p>
        </div>
      </div>
    );
  }

  // Empty state
  if (results.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]">
        <div className="flex h-64 flex-col items-center justify-center gap-4">
          <Search className="h-12 w-12 text-[var(--foreground-muted)]" />
          <div className="text-center">
            <p className="font-medium text-[var(--foreground)]">{t('noResults')}</p>
            <p className="mt-1 text-sm text-[var(--foreground-muted)]">
              {t('noResultsDesc')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] overflow-hidden">
      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--background)]">
              <th className="px-4 py-3 text-left">
                <SortButton field="ticker" currentField={sortField} onSort={handleSort}>
                  {t('ticker')}
                </SortButton>
              </th>
              <th className="px-4 py-3 text-left">
                <SortButton field="name" currentField={sortField} onSort={handleSort}>
                  {t('name')}
                </SortButton>
              </th>
              <th className="px-4 py-3 text-right">
                <SortButton field="current_price" currentField={sortField} onSort={handleSort}>
                  {t('price')}
                </SortButton>
              </th>
              <th className="px-4 py-3 text-center text-sm font-semibold text-[var(--foreground)]">
                {t('match')}
              </th>
              <th className="px-4 py-3 text-center text-sm font-semibold text-[var(--foreground)]">
                {t('details')}
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedResults.map((result) => (
              <TableRow
                key={result.ticker}
                result={result}
                isExpanded={expandedRow === result.ticker}
                onToggle={toggleRow}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden divide-y divide-[var(--border)]">
        {sortedResults.map((result) => (
          <MobileCard
            key={result.ticker}
            result={result}
            isExpanded={expandedRow === result.ticker}
            onToggle={toggleRow}
          />
        ))}
      </div>
    </div>
  );
}

interface RowProps {
  result: ScreeningResult;
  isExpanded: boolean;
  onToggle: (ticker: string) => void;
}

/**
 * Desktop table row component
 */
function TableRow({ result, isExpanded, onToggle }: RowProps) {
  const t = useTranslations('screening');
  return (
    <>
      <tr
        className={`border-b border-[var(--border)] transition-colors ${
          isExpanded ? 'bg-[var(--background)]' : 'hover:bg-[var(--background)]'
        }`}
      >
        <td className="px-4 py-3">
          <span className="font-mono font-medium text-[var(--color-primary)]">
            {result.ticker}
          </span>
        </td>
        <td className="px-4 py-3 text-[var(--foreground)]">{result.name}</td>
        <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
          {formatPrice(result.current_price)}
        </td>
        <td className="px-4 py-3 text-center">
          {result.matched ? (
            <CheckCircle className="inline-block h-5 w-5 text-green-600 dark:text-green-400" />
          ) : (
            <XCircle className="inline-block h-5 w-5 text-red-600 dark:text-red-400" />
          )}
        </td>
        <td className="px-4 py-3 text-center">
          <button
            type="button"
            onClick={() => onToggle(result.ticker)}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            aria-label={isExpanded ? t('hideDetails') : t('showDetails')}
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <ChevronUp className="h-5 w-5" />
            ) : (
              <ChevronDown className="h-5 w-5" />
            )}
          </button>
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td
            colSpan={5}
            className="border-b border-[var(--border)] bg-[var(--background)] px-4 py-4"
          >
            <ConditionDetails conditions={result.conditions} />
          </td>
        </tr>
      )}
    </>
  );
}

/**
 * Mobile card component for responsive display
 */
function MobileCard({ result, isExpanded, onToggle }: RowProps) {
  const t = useTranslations('screening');
  return (
    <div className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-medium text-[var(--color-primary)]">
              {result.ticker}
            </span>
            {result.matched ? (
              <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
            ) : (
              <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
            )}
          </div>
          <p className="mt-1 text-sm text-[var(--foreground)]">{result.name}</p>
        </div>
        <div className="text-right">
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatPrice(result.current_price)}
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => onToggle(result.ticker)}
        className="mt-3 flex w-full items-center justify-center gap-1 rounded-lg border border-[var(--border)] py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--background)] transition-colors"
        aria-expanded={isExpanded}
      >
        {isExpanded ? (
          <>
            <ChevronUp className="h-4 w-4" />
            {t('hideDetails')}
          </>
        ) : (
          <>
            <ChevronDown className="h-4 w-4" />
            {t('showDetails')}
          </>
        )}
      </button>

      {isExpanded && (
        <div className="mt-3">
          <ConditionDetails conditions={result.conditions} />
        </div>
      )}
    </div>
  );
}
