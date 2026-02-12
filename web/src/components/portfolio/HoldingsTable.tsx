'use client';

import { useState, useMemo, useCallback } from 'react';
import { ArrowUpDown, Edit2, Trash2, TrendingUp, TrendingDown } from 'lucide-react';
import type { Holding } from '@/lib/types';

type SortField = 'ticker' | 'name' | 'quantity' | 'avg_price' | 'current_price' | 'market_value' | 'pnl' | 'pnl_pct';
type SortDirection = 'asc' | 'desc';

interface HoldingsTableProps {
  /** Holdings data to display */
  holdings: Holding[];
  /** Whether data is loading */
  isLoading?: boolean;
  /** Callback when edit button is clicked */
  onEdit?: (holding: Holding) => void;
  /** Callback when delete button is clicked */
  onDelete?: (holding: Holding) => void;
}

interface SortButtonProps {
  field: SortField;
  currentField: SortField;
  direction: SortDirection;
  children: React.ReactNode;
  onSort: (field: SortField) => void;
  align?: 'left' | 'right';
}

/**
 * Sort button component for table headers
 */
function SortButton({ field, currentField, direction, children, onSort, align = 'left' }: SortButtonProps) {
  const isActive = currentField === field;
  return (
    <button
      type="button"
      onClick={() => onSort(field)}
      className={`flex items-center gap-1 font-semibold text-[var(--foreground)] hover:text-[var(--color-primary)] transition-colors ${
        align === 'right' ? 'ml-auto' : ''
      }`}
    >
      {children}
      <ArrowUpDown
        className={`h-4 w-4 ${
          isActive ? 'text-[var(--color-primary)]' : 'text-[var(--foreground-muted)]'
        } ${isActive && direction === 'desc' ? 'rotate-180' : ''}`}
      />
    </button>
  );
}

/**
 * Format a number as currency
 */
function formatCurrency(value: number | null, currency: string = 'USD'): string {
  if (value === null) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a number as percentage
 */
function formatPercent(value: number | null): string {
  if (value === null) return '-';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Format quantity with appropriate decimal places
 */
function formatQuantity(value: number): string {
  if (Number.isInteger(value)) {
    return value.toLocaleString();
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  });
}

/**
 * Get color class based on P&L value
 */
function getPnlColorClass(value: number | null): string {
  if (value === null) return 'text-[var(--foreground-muted)]';
  if (value > 0) return 'text-green-600 dark:text-green-400';
  if (value < 0) return 'text-red-600 dark:text-red-400';
  return 'text-[var(--foreground-muted)]';
}

/**
 * Table displaying portfolio holdings with sorting, edit, and delete functionality
 */
export default function HoldingsTable({
  holdings,
  isLoading,
  onEdit,
  onDelete,
}: HoldingsTableProps) {
  const [sortField, setSortField] = useState<SortField>('ticker');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const sortedHoldings = useMemo(() => {
    return [...holdings].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'ticker':
          comparison = a.ticker.localeCompare(b.ticker);
          break;
        case 'name':
          comparison = (a.name || '').localeCompare(b.name || '');
          break;
        case 'quantity':
          comparison = a.quantity - b.quantity;
          break;
        case 'avg_price':
          comparison = a.avg_price - b.avg_price;
          break;
        case 'current_price':
          comparison = (a.current_price ?? 0) - (b.current_price ?? 0);
          break;
        case 'market_value':
          comparison = (a.market_value ?? 0) - (b.market_value ?? 0);
          break;
        case 'pnl':
          comparison = (a.pnl ?? 0) - (b.pnl ?? 0);
          break;
        case 'pnl_pct':
          comparison = (a.pnl_pct ?? 0) - (b.pnl_pct ?? 0);
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [holdings, sortField, sortDirection]);

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

  // Loading state
  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]">
        <div className="flex h-64 flex-col items-center justify-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--color-primary)]" />
          <p className="text-[var(--foreground-muted)]">Loading holdings...</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (holdings.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]">
        <div className="flex h-64 flex-col items-center justify-center gap-4">
          <TrendingUp className="h-12 w-12 text-[var(--foreground-muted)]" />
          <div className="text-center">
            <p className="font-medium text-[var(--foreground)]">No holdings yet</p>
            <p className="mt-1 text-sm text-[var(--foreground-muted)]">
              Add your first holding to start tracking your portfolio.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] overflow-hidden">
      {/* Desktop Table View */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--background)]">
              <th className="px-4 py-3 text-left">
                <SortButton field="ticker" currentField={sortField} direction={sortDirection} onSort={handleSort}>
                  Ticker
                </SortButton>
              </th>
              <th className="px-4 py-3 text-left">
                <SortButton field="name" currentField={sortField} direction={sortDirection} onSort={handleSort}>
                  Name
                </SortButton>
              </th>
              <th className="px-4 py-3 text-right">
                <SortButton field="quantity" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  Qty
                </SortButton>
              </th>
              <th className="px-4 py-3 text-right">
                <SortButton field="avg_price" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  Avg Price
                </SortButton>
              </th>
              <th className="px-4 py-3 text-right">
                <SortButton field="current_price" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  Current
                </SortButton>
              </th>
              <th className="px-4 py-3 text-right">
                <SortButton field="market_value" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  Value
                </SortButton>
              </th>
              <th className="px-4 py-3 text-right">
                <SortButton field="pnl" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  P&L
                </SortButton>
              </th>
              <th className="px-4 py-3 text-right">
                <SortButton field="pnl_pct" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  P&L %
                </SortButton>
              </th>
              <th className="px-4 py-3 text-center text-sm font-semibold text-[var(--foreground)]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedHoldings.map((holding) => (
              <tr
                key={holding.ticker}
                className="border-b border-[var(--border)] hover:bg-[var(--background)] transition-colors"
              >
                <td className="px-4 py-3">
                  <span className="font-mono font-medium text-[var(--color-primary)]">
                    {holding.ticker}
                  </span>
                </td>
                <td className="px-4 py-3 text-[var(--foreground)]">
                  {holding.name || '-'}
                </td>
                <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                  {formatQuantity(holding.quantity)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                  {formatCurrency(holding.avg_price, holding.currency)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                  {formatCurrency(holding.current_price, holding.currency)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                  {formatCurrency(holding.market_value, holding.currency)}
                </td>
                <td className={`px-4 py-3 text-right font-mono ${getPnlColorClass(holding.pnl)}`}>
                  <span className="flex items-center justify-end gap-1">
                    {holding.pnl !== null && holding.pnl !== 0 && (
                      holding.pnl > 0 ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <TrendingDown className="h-4 w-4" />
                      )
                    )}
                    {formatCurrency(holding.pnl, holding.currency)}
                  </span>
                </td>
                <td className={`px-4 py-3 text-right font-mono ${getPnlColorClass(holding.pnl_pct)}`}>
                  {formatPercent(holding.pnl_pct)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-2">
                    {onEdit && (
                      <button
                        type="button"
                        onClick={() => onEdit(holding)}
                        className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
                        aria-label={`Edit ${holding.ticker}`}
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                    )}
                    {onDelete && (
                      <button
                        type="button"
                        onClick={() => onDelete(holding)}
                        className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/50 dark:hover:text-red-400 transition-colors"
                        aria-label={`Delete ${holding.ticker}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile/Tablet Card View */}
      <div className="lg:hidden divide-y divide-[var(--border)]">
        {sortedHoldings.map((holding) => (
          <MobileCard
            key={holding.ticker}
            holding={holding}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
}

interface MobileCardProps {
  holding: Holding;
  onEdit?: (holding: Holding) => void;
  onDelete?: (holding: Holding) => void;
}

/**
 * Mobile card component for responsive display
 */
function MobileCard({ holding, onEdit, onDelete }: MobileCardProps) {
  return (
    <div className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-medium text-[var(--color-primary)]">
              {holding.ticker}
            </span>
            {holding.pnl !== null && holding.pnl !== 0 && (
              holding.pnl > 0 ? (
                <TrendingUp className="h-4 w-4 text-green-600 dark:text-green-400" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400" />
              )
            )}
          </div>
          <p className="mt-1 text-sm text-[var(--foreground)]">{holding.name || '-'}</p>
        </div>
        <div className="flex items-center gap-1">
          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(holding)}
              className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
              aria-label={`Edit ${holding.ticker}`}
            >
              <Edit2 className="h-4 w-4" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={() => onDelete(holding)}
              className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/50 dark:hover:text-red-400 transition-colors"
              aria-label={`Delete ${holding.ticker}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-[var(--foreground-muted)]">Quantity</p>
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatQuantity(holding.quantity)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">Avg Price</p>
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatCurrency(holding.avg_price, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">Current Price</p>
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatCurrency(holding.current_price, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">Market Value</p>
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatCurrency(holding.market_value, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">P&L</p>
          <p className={`font-mono font-medium ${getPnlColorClass(holding.pnl)}`}>
            {formatCurrency(holding.pnl, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">P&L %</p>
          <p className={`font-mono font-medium ${getPnlColorClass(holding.pnl_pct)}`}>
            {formatPercent(holding.pnl_pct)}
          </p>
        </div>
      </div>
    </div>
  );
}
