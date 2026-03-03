'use client';

import { useState, useMemo, useCallback } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { ArrowUpDown, Edit2, Trash2, TrendingUp, TrendingDown, BarChart3, Banknote, Shield } from 'lucide-react';
import type { Holding } from '@/lib/types';
import { formatCurrency as formatCurrencyUtil, formatQuantity as formatQuantityUtil, formatPercent as formatPercentUtil } from '@/lib/format';
import { classifyMarket, normalizeSector, MARKET_COLORS, SECTOR_COLORS } from './AllocationCharts';

type SortField = 'ticker' | 'name' | 'sector' | 'market' | 'quantity' | 'avg_price' | 'current_price' | 'market_value' | 'pnl' | 'pnl_pct';
type SortDirection = 'asc' | 'desc';

interface HoldingsTableProps {
  /** Holdings data to display */
  holdings: Holding[];
  /** Whether data is loading */
  isLoading?: boolean;
  /** Callback when a holding row is clicked */
  onRowClick?: (holding: Holding) => void;
  /** Callback when edit button is clicked */
  onEdit?: (holding: Holding) => void;
  /** Callback when delete button is clicked */
  onDelete?: (holding: Holding) => void;
  /** Callback when analysis button is clicked */
  onAnalyze?: (holding: Holding) => void;
  /** Callback when sell button is clicked */
  onSell?: (holding: Holding) => void;
  /** Callback when sell rules button is clicked */
  onSellRules?: (holding: Holding) => void;
  /** Per-ticker current price change direction for transient highlight */
  priceChangeDirection?: Record<string, 'up' | 'down'>;
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
      className={`flex items-center gap-1 text-[13px] font-semibold text-[var(--foreground)] hover:text-[var(--color-primary)] transition-colors ${
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

// Local wrappers that capture the locale from the component tree.
// The actual implementations live in @/lib/format.

const SECTOR_I18N: Record<string, string> = {
  Technology: 'technology', Financials: 'financials', Consumer: 'consumer',
  Healthcare: 'healthcare', Energy: 'energy', Industrials: 'industrials',
  Materials: 'materials', 'Real Estate': 'realEstate', Utilities: 'utilities',
  Communication: 'communication', Others: 'others',
};

const MARKET_I18N: Record<string, string> = {
  KOSPI: 'kospi', KOSDAQ: 'kosdaq', US: 'us', ETF: 'etf', unknown: 'unknown',
};

function sectorI18nKey(sector: string): string {
  return SECTOR_I18N[sector] ?? 'others';
}

function marketI18nKey(market: string): string {
  return MARKET_I18N[market] ?? 'unknown';
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
  onRowClick,
  onEdit,
  onDelete,
  onAnalyze,
  onSell,
  onSellRules,
  priceChangeDirection,
}: HoldingsTableProps) {
  const t = useTranslations('portfolio');
  const ta = useTranslations('allocation');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency?: string) => formatCurrencyUtil(value, currency, locale);
  const formatPercent = (value: number | null) => formatPercentUtil(value);
  const formatQuantity = (value: number) => formatQuantityUtil(value, locale);
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
        case 'sector':
          comparison = normalizeSector(a.sector).localeCompare(normalizeSector(b.sector));
          break;
        case 'market':
          comparison = classifyMarket(a.ticker).localeCompare(classifyMarket(b.ticker));
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
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  }, [sortField]);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]">
        <div className="flex h-64 flex-col items-center justify-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--color-primary)]" />
          <p className="text-[var(--foreground-muted)]">{t('loadingHoldings')}</p>
        </div>
      </div>
    );
  }

  if (holdings.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]">
        <div className="flex h-64 flex-col items-center justify-center gap-4">
          <TrendingUp className="h-12 w-12 text-[var(--foreground-muted)]" />
          <div className="text-center">
            <p className="font-medium text-[var(--foreground)]">{t('noHoldingsTitle')}</p>
            <p className="mt-1 text-sm text-[var(--foreground-muted)]">
              {t('addFirstHolding')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] overflow-hidden">
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--background)]/50">
              <th className="px-4 py-2.5 text-left">
                <SortButton field="name" currentField={sortField} direction={sortDirection} onSort={handleSort}>
                  {t('name')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-left">
                <SortButton field="sector" currentField={sortField} direction={sortDirection} onSort={handleSort}>
                  {t('sector')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-left">
                <SortButton field="market" currentField={sortField} direction={sortDirection} onSort={handleSort}>
                  {t('market')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-right">
                <SortButton field="quantity" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  {t('qty')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-right">
                <SortButton field="avg_price" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  {t('avgPrice')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-right">
                <SortButton field="current_price" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  {t('currentPrice')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-right">
                <SortButton field="market_value" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  {t('value')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-right">
                <SortButton field="pnl" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  {t('pnl')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-right">
                <SortButton field="pnl_pct" currentField={sortField} direction={sortDirection} onSort={handleSort} align="right">
                  {t('pnlPct')}
                </SortButton>
              </th>
              <th className="px-4 py-2.5 text-center text-[13px] font-semibold text-[var(--foreground)]">
                {t('actions')}
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedHoldings.map((holding) => (
              <tr
                key={holding.ticker}
                onClick={() => onRowClick?.(holding)}
                className={`border-b border-[var(--border)] hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
              >
                <td className="px-4 py-2.5 text-[var(--foreground)]">
                  {holding.name || holding.ticker}
                </td>
                <td className="px-4 py-2.5">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--background)] px-2.5 py-0.5 text-xs text-[var(--foreground-muted)]">
                    <span className="inline-block h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: SECTOR_COLORS[normalizeSector(holding.sector)] ?? '#94a3b8' }} />
                    {ta(sectorI18nKey(normalizeSector(holding.sector)))}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--background)] px-2.5 py-0.5 text-xs text-[var(--foreground-muted)]">
                    <span className="inline-block h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: MARKET_COLORS[classifyMarket(holding.ticker)] ?? '#94a3b8' }} />
                    {ta(marketI18nKey(classifyMarket(holding.ticker)))}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-[var(--foreground)]">
                  {formatQuantity(holding.quantity)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-[var(--foreground)]">
                  {formatCurrency(holding.avg_price, holding.currency)}
                </td>
                <td
                  className={`px-4 py-2.5 text-right font-mono transition-colors ${getPnlColorClass(holding.change_pct)} ${
                    priceChangeDirection?.[holding.ticker] === 'up'
                      ? 'bg-red-100/70 dark:bg-red-900/30'
                      : priceChangeDirection?.[holding.ticker] === 'down'
                      ? 'bg-blue-100/70 dark:bg-blue-900/30'
                      : ''
                  }`}
                >
                  <span className="flex items-center justify-end gap-1">
                    {holding.change_pct !== null && holding.change_pct !== undefined && holding.change_pct !== 0 && (
                      holding.change_pct > 0 ? (
                        <TrendingUp className="h-3.5 w-3.5" />
                      ) : (
                        <TrendingDown className="h-3.5 w-3.5" />
                      )
                    )}
                    {formatCurrency(holding.current_price, holding.currency)}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-[var(--foreground)]">
                  {formatCurrency(holding.market_value, holding.currency)}
                </td>
                <td className={`px-4 py-2.5 text-right font-mono ${getPnlColorClass(holding.pnl)}`}>
                  <span className="flex items-center justify-end gap-1">
                    {holding.pnl !== null && holding.pnl !== 0 && (
                      holding.pnl > 0 ? (
                        <TrendingUp className="h-3.5 w-3.5" />
                      ) : (
                        <TrendingDown className="h-3.5 w-3.5" />
                      )
                    )}
                    {formatCurrency(holding.pnl, holding.currency)}
                  </span>
                </td>
                <td className={`px-4 py-2.5 text-right font-mono ${getPnlColorClass(holding.pnl_pct)}`}>
                  {formatPercent(holding.pnl_pct)}
                </td>
                <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
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
                    {onAnalyze && (
                      <button
                        type="button"
                        onClick={() => onAnalyze(holding)}
                        className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
                        aria-label={`Analyze ${holding.ticker}`}
                        title={t('openAnalysis')}
                      >
                        <BarChart3 className="h-4 w-4" />
                      </button>
                    )}
                    {onSellRules && (
                      <button
                        type="button"
                        onClick={() => onSellRules(holding)}
                        className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
                        aria-label={`${t('sellRulesTitle')} ${holding.ticker}`}
                        title={t('sellRulesTitle')}
                      >
                        <Shield className="h-4 w-4" />
                      </button>
                    )}
                    {onSell && (
                      <button
                        type="button"
                        onClick={() => onSell(holding)}
                        className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-orange-100 hover:text-orange-600 dark:hover:bg-orange-900/50 dark:hover:text-orange-400 transition-colors"
                        aria-label={`${t('sell')} ${holding.ticker}`}
                        title={t('sell')}
                      >
                        <Banknote className="h-4 w-4" />
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

      <div className="lg:hidden divide-y divide-[var(--border)]">
        {sortedHoldings.map((holding) => (
          <MobileCard
            key={holding.ticker}
            holding={holding}
            onRowClick={onRowClick}
            onEdit={onEdit}
            onDelete={onDelete}
            onAnalyze={onAnalyze}
            onSell={onSell}
            onSellRules={onSellRules}
            priceChangeDirection={priceChangeDirection}
          />
        ))}
      </div>
    </div>
  );
}

interface MobileCardProps {
  holding: Holding;
  onRowClick?: (holding: Holding) => void;
  onEdit?: (holding: Holding) => void;
  onDelete?: (holding: Holding) => void;
  onAnalyze?: (holding: Holding) => void;
  onSell?: (holding: Holding) => void;
  onSellRules?: (holding: Holding) => void;
  priceChangeDirection?: Record<string, 'up' | 'down'>;
}

/**
 * Mobile card component for responsive display
 */
function MobileCard({ holding, onRowClick, onEdit, onDelete, onAnalyze, onSell, onSellRules, priceChangeDirection }: MobileCardProps) {
  const t = useTranslations('portfolio');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency?: string) => formatCurrencyUtil(value, currency, locale);
  const formatPercent = (value: number | null) => formatPercentUtil(value);
  const formatQuantity = (value: number) => formatQuantityUtil(value, locale);

  return (
    <div
      className={`p-3 ${onRowClick ? 'cursor-pointer' : ''}`}
      onClick={() => onRowClick?.(holding)}
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-medium text-[var(--color-primary)]">
              {holding.ticker}
            </span>
            {holding.change_pct !== null && holding.change_pct !== undefined && holding.change_pct !== 0 && (
              holding.change_pct > 0 ? (
                <TrendingUp className="h-4 w-4 text-green-600 dark:text-green-400" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400" />
              )
            )}
          </div>
          <p className="mt-1 text-sm text-[var(--foreground)]">{holding.name || '-'}</p>
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
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
          {onSellRules && (
            <button
              type="button"
              onClick={() => onSellRules(holding)}
              className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
              aria-label={`${t('sellRulesTitle')} ${holding.ticker}`}
              title={t('sellRulesTitle')}
            >
              <Shield className="h-4 w-4" />
            </button>
          )}
          {onSell && (
            <button
              type="button"
              onClick={() => onSell(holding)}
              className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-orange-100 hover:text-orange-600 dark:hover:bg-orange-900/50 dark:hover:text-orange-400 transition-colors"
              aria-label={`${t('sell')} ${holding.ticker}`}
              title={t('sell')}
            >
              <Banknote className="h-4 w-4" />
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
          {onAnalyze && (
            <button
              type="button"
              onClick={() => onAnalyze(holding)}
              className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
              aria-label={`Analyze ${holding.ticker}`}
              title={t('openAnalysis')}
            >
              <BarChart3 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-[var(--foreground-muted)]">{t('quantity')}</p>
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatQuantity(holding.quantity)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">{t('avgPrice')}</p>
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatCurrency(holding.avg_price, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">{t('currentPrice')}</p>
          <p
            className={`font-mono font-medium inline-flex items-center gap-1 rounded px-1 transition-colors ${getPnlColorClass(holding.change_pct)} ${
              priceChangeDirection?.[holding.ticker] === 'up'
                ? 'bg-red-100/70 dark:bg-red-900/30'
                : priceChangeDirection?.[holding.ticker] === 'down'
                ? 'bg-blue-100/70 dark:bg-blue-900/30'
                : ''
            }`}
          >
            {holding.change_pct !== null && holding.change_pct !== undefined && holding.change_pct !== 0 && (
              holding.change_pct > 0 ? (
                <TrendingUp className="h-3.5 w-3.5" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5" />
              )
            )}
            {formatCurrency(holding.current_price, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">{t('value')}</p>
          <p className="font-mono font-medium text-[var(--foreground)]">
            {formatCurrency(holding.market_value, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">{t('pnl')}</p>
          <p className={`font-mono font-medium ${getPnlColorClass(holding.pnl)}`}>
            {formatCurrency(holding.pnl, holding.currency)}
          </p>
        </div>
        <div>
          <p className="text-[var(--foreground-muted)]">{t('pnlPct')}</p>
          <p className={`font-mono font-medium ${getPnlColorClass(holding.pnl_pct)}`}>
            {formatPercent(holding.pnl_pct)}
          </p>
        </div>
      </div>
    </div>
  );
}
