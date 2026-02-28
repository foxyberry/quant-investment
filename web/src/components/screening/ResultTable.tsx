'use client';

import { useState, useMemo, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  Download,
  Save,
  Construction,
  Rocket,
  Globe,
  Play,
  SearchX,
  X,
} from 'lucide-react';
import type { ScreeningResult } from '@/lib/types';
import ConditionDetails from './ConditionDetails';

type SortField = 'ticker' | 'name' | 'current_price' | 'change_pct' | 'volume' | 'score';
type SortDirection = 'asc' | 'desc';

const PAGE_SIZE = 20;

interface ResultTableProps {
  results: ScreeningResult[];
  isLoading?: boolean;
  hasRun?: boolean;
  onRunScreening?: () => void;
  onSave?: () => void;
}

interface SortButtonProps {
  field: SortField;
  currentField: SortField;
  currentDirection: SortDirection;
  children: React.ReactNode;
  onSort: (field: SortField) => void;
  className?: string;
}

function SortButton({ field, currentField, currentDirection, children, onSort, className = '' }: SortButtonProps) {
  const isActive = currentField === field;
  return (
    <button
      type="button"
      onClick={() => onSort(field)}
      className={`flex items-center gap-1 whitespace-nowrap text-sm font-semibold leading-5 text-[var(--foreground)] hover:text-[var(--color-primary)] transition-colors ${className}`}
    >
      {children}
      {isActive ? (
        currentDirection === 'asc' ? (
          <ChevronUp className="h-3.5 w-3.5 text-[var(--color-primary)]" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-[var(--color-primary)]" />
        )
      ) : (
        <ArrowUpDown className="h-3.5 w-3.5 text-[var(--foreground-muted)]" />
      )}
    </button>
  );
}

function formatPrice(price: number | null | undefined): string {
  if (price == null) return '-';
  return price.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatVolume(vol: number | null | undefined): string {
  if (vol == null) return '-';
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`;
  return vol.toLocaleString();
}

function formatChangePct(pct: number | null | undefined): string {
  if (pct == null) return '-';
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

function changePctColor(pct: number | null | undefined): string {
  if (pct == null) return 'text-[var(--foreground-muted)]';
  if (pct > 0) return 'text-red-600 dark:text-red-400';
  if (pct < 0) return 'text-blue-600 dark:text-blue-400';
  return 'text-[var(--foreground)]';
}

function exportCsv(results: ScreeningResult[]) {
  const headers = ['Rank', 'Ticker', 'Name', 'Market', 'Price', 'Change%', 'Volume', 'Score', 'Matched'];
  const rows = results.map((r, i) => [
    i + 1,
    r.ticker,
    `"${r.name.replace(/"/g, '""')}"`,
    r.market ?? '',
    r.current_price ?? '',
    r.change_pct != null ? r.change_pct.toFixed(2) : '',
    r.volume ?? '',
    r.score != null ? r.score.toFixed(1) : '',
    r.matched ? 'Y' : 'N',
  ]);
  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `screening_results_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ResultTable({ results, isLoading, hasRun, onRunScreening, onSave }: ResultTableProps) {
  const t = useTranslations('screening');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<ScreeningResult | null>(null);
  const [sortField, setSortField] = useState<SortField>('score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [currentPage, setCurrentPage] = useState(1);

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
        case 'current_price':
          comparison = (a.current_price ?? 0) - (b.current_price ?? 0);
          break;
        case 'change_pct':
          comparison = (a.change_pct ?? 0) - (b.change_pct ?? 0);
          break;
        case 'volume':
          comparison = (a.volume ?? 0) - (b.volume ?? 0);
          break;
        case 'score':
          comparison = (a.score ?? 0) - (b.score ?? 0);
          break;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [results, sortField, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(sortedResults.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const pagedResults = sortedResults.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const showFrom = sortedResults.length > 0 ? (safePage - 1) * PAGE_SIZE + 1 : 0;
  const showTo = Math.min(safePage * PAGE_SIZE, sortedResults.length);

  const handleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortDirection(field === 'score' ? 'desc' : 'asc');
      return field;
    });
    setCurrentPage(1);
  }, []);

  const toggleRow = useCallback((ticker: string) => {
    setExpandedRow((prev) => (prev === ticker ? null : ticker));
  }, []);

  const openResultModal = useCallback((result: ScreeningResult) => {
    setSelectedResult(result);
  }, []);

  const closeResultModal = useCallback(() => {
    setSelectedResult(null);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)]">
        <div className="flex h-64 flex-col items-center justify-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--color-primary)]" />
          <p className="text-[var(--foreground-muted)]">{t('runningScreening')}</p>
        </div>
      </div>
    );
  }

  // Empty state — no screening has been run yet
  if (!hasRun && results.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-8">
        <div className="mx-auto max-w-md text-center">
          <p className="mb-2 text-lg font-semibold text-[var(--foreground)]">
            {t('noResults')}
          </p>
          <p className="mb-6 text-sm text-[var(--foreground-muted)]">
            {t('noResultsDesc')}
          </p>
          {onRunScreening && (
            <button
              type="button"
              onClick={onRunScreening}
              className="mb-8 inline-flex items-center gap-2 rounded-lg bg-[var(--color-primary)] px-5 py-2.5 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            >
              <Play className="h-4 w-4" />
              {t('emptyGuideActionBtn')}
            </button>
          )}
        </div>
        <p className="mb-4 text-center text-base font-semibold text-[var(--foreground)]">
          {t('emptyGuideTitle')}
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          <GuideCard
            icon={<Construction className="h-6 w-6 text-amber-500" />}
            title={t('guideStrategyBuilder')}
            description={t('guideStrategyBuilderDesc')}
            cta={t('guideStrategyBuilderCta')}
            href="/strategy"
          />
          <GuideCard
            icon={<Rocket className="h-6 w-6 text-purple-500" />}
            title={t('guideBuiltinPresets')}
            description={t('guideBuiltinPresetsDesc')}
            cta={t('guideBuiltinPresetsCta')}
          />
          <GuideCard
            icon={<Globe className="h-6 w-6 text-blue-500" />}
            title={t('guideMultiUniverse')}
            description={t('guideMultiUniverseDesc')}
            cta={t('guideMultiUniverseCta')}
          />
        </div>
      </div>
    );
  }

  // Ran screening but no matches found
  if (hasRun && results.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-8">
        <div className="flex flex-col items-center justify-center gap-3">
          <SearchX className="h-10 w-10 text-[var(--foreground-muted)]" />
          <p className="text-lg font-semibold text-[var(--foreground)]">
            {t('noResultsFound')}
          </p>
          <p className="text-sm text-[var(--foreground-muted)]">
            {t('noResultsFoundDesc')}
          </p>
        </div>
      </div>
    );
  }

  const colCount = 9;

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] overflow-hidden">
      {/* Toolbar: Save + Export CSV */}
      <div className="flex items-center justify-end gap-2 border-b border-[var(--border)] px-4 py-2">
        {onSave && (
          <button
            type="button"
            onClick={onSave}
            disabled={results.length === 0}
            className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--border)]/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="h-3.5 w-3.5" />
            {t('saveResult')}
          </button>
        )}
        <button
          type="button"
          onClick={() => exportCsv(sortedResults)}
          className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--border)]/50 transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          {t('exportCsv')}
        </button>
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--background)]">
              <th className="w-14 whitespace-nowrap px-3 py-3 text-center text-sm font-semibold text-[var(--foreground)]">{t('rank')}</th>
              <th className="whitespace-nowrap px-3 py-3 text-left text-sm font-semibold text-[var(--foreground)]">
                <SortButton field="ticker" currentField={sortField} currentDirection={sortDirection} onSort={handleSort}>
                  {t('ticker')}
                </SortButton>
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-left text-sm font-semibold text-[var(--foreground)]">
                <SortButton field="name" currentField={sortField} currentDirection={sortDirection} onSort={handleSort}>
                  {t('name')}
                </SortButton>
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-center text-sm font-semibold text-[var(--foreground)]">{t('market')}</th>
              <th className="whitespace-nowrap px-3 py-3 text-right text-sm font-semibold text-[var(--foreground)]">
                <SortButton field="current_price" currentField={sortField} currentDirection={sortDirection} onSort={handleSort} className="justify-end">
                  {t('price')}
                </SortButton>
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-right text-sm font-semibold text-[var(--foreground)]">
                <SortButton field="change_pct" currentField={sortField} currentDirection={sortDirection} onSort={handleSort} className="justify-end">
                  {t('changePct')}
                </SortButton>
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-right text-sm font-semibold text-[var(--foreground)]">
                <SortButton field="volume" currentField={sortField} currentDirection={sortDirection} onSort={handleSort} className="justify-end">
                  {t('volume')}
                </SortButton>
              </th>
              <th className="whitespace-nowrap px-3 py-3 text-right text-sm font-semibold text-[var(--foreground)]">
                <SortButton field="score" currentField={sortField} currentDirection={sortDirection} onSort={handleSort} className="justify-end">
                  {t('score')}
                </SortButton>
              </th>
              <th className="w-10 whitespace-nowrap px-2 py-3 text-center text-sm font-semibold text-[var(--foreground)]" />
            </tr>
          </thead>
          <tbody>
            {pagedResults.map((result, idx) => {
              const rank = (safePage - 1) * PAGE_SIZE + idx + 1;
              return (
                <TableRow
                  key={result.ticker}
                  result={result}
                  rank={rank}
                  colCount={colCount}
                  isExpanded={expandedRow === result.ticker}
                  onToggle={toggleRow}
                  onOpen={openResultModal}
                />
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden divide-y divide-[var(--border)]">
        {pagedResults.map((result, idx) => {
          const rank = (safePage - 1) * PAGE_SIZE + idx + 1;
          return (
            <MobileCard
              key={result.ticker}
              result={result}
              rank={rank}
              isExpanded={expandedRow === result.ticker}
              onToggle={toggleRow}
              onOpen={openResultModal}
            />
          );
        })}
      </div>

      {selectedResult && (
        <ResultDetailModal result={selectedResult} onClose={closeResultModal} />
      )}

      {/* Pagination */}
      {sortedResults.length > PAGE_SIZE && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] px-4 py-3">
          <span className="text-xs text-[var(--foreground-muted)]">
            {t('showing', { from: showFrom, to: showTo, total: sortedResults.length })}
          </span>
          <div className="flex items-center gap-1">
            <PaginationButton
              onClick={() => setCurrentPage(1)}
              disabled={safePage <= 1}
              aria-label={t('first')}
            >
              <ChevronsLeft className="h-4 w-4" />
            </PaginationButton>
            <PaginationButton
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              aria-label={t('previous')}
            >
              <ChevronLeft className="h-4 w-4" />
            </PaginationButton>
            {pageNumbers(safePage, totalPages).map((p) =>
              p === '...' ? (
                <span key={`ellipsis-${p}`} className="px-1 text-xs text-[var(--foreground-muted)]">...</span>
              ) : (
                <PaginationButton
                  key={p}
                  onClick={() => setCurrentPage(p as number)}
                  active={p === safePage}
                >
                  {p}
                </PaginationButton>
              )
            )}
            <PaginationButton
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              aria-label={t('next')}
            >
              <ChevronRight className="h-4 w-4" />
            </PaginationButton>
            <PaginationButton
              onClick={() => setCurrentPage(totalPages)}
              disabled={safePage >= totalPages}
              aria-label={t('last')}
            >
              <ChevronsRight className="h-4 w-4" />
            </PaginationButton>
          </div>
        </div>
      )}
    </div>
  );
}

/* ----------- Sub-components ----------- */

function pageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | '...')[] = [1];
  if (current > 3) pages.push('...');
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i);
  }
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
}

interface PaginationButtonProps {
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  children: React.ReactNode;
  'aria-label'?: string;
}

function PaginationButton({ onClick, disabled, active, children, ...rest }: PaginationButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex h-8 min-w-[2rem] items-center justify-center rounded-md px-2 text-xs font-medium transition-colors ${
        active
          ? 'bg-[var(--color-primary)] text-white'
          : disabled
            ? 'text-[var(--foreground-muted)]/40 cursor-not-allowed'
            : 'text-[var(--foreground)] hover:bg-[var(--border)]/50'
      }`}
      {...rest}
    >
      {children}
    </button>
  );
}

interface GuideCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  cta?: string;
  href?: string;
}

function GuideCard({ icon, title, description, cta, href }: GuideCardProps) {
  const Wrapper = href ? 'a' : 'div';
  return (
    <Wrapper
      {...(href ? { href } : {})}
      className={`flex flex-col items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--background)] p-5 text-center transition-colors ${
        href ? 'hover:border-[var(--color-primary)]/50 hover:bg-[var(--color-primary)]/5 cursor-pointer' : ''
      }`}
    >
      {icon}
      <div>
        <p className="font-medium text-[var(--foreground)]">{title}</p>
        <p className="mt-1 text-xs text-[var(--foreground-muted)]">{description}</p>
      </div>
      {cta && (
        <span className="mt-1 text-xs font-medium text-[var(--color-primary)]">{cta}</span>
      )}
    </Wrapper>
  );
}

interface RowProps {
  result: ScreeningResult;
  rank: number;
  isExpanded: boolean;
  onToggle: (ticker: string) => void;
  onOpen: (result: ScreeningResult) => void;
  colCount?: number;
}

function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-[var(--foreground-muted)]">-</span>;
  let color = 'text-[var(--foreground)]';
  if (score >= 80) color = 'text-green-600 dark:text-green-400';
  else if (score >= 50) color = 'text-amber-600 dark:text-amber-400';
  else color = 'text-red-600 dark:text-red-400';
  return <span className={`font-semibold ${color}`}>{score.toFixed(1)}</span>;
}

function TableRow({ result, rank, colCount = 9, isExpanded, onToggle, onOpen }: RowProps) {
  const t = useTranslations('screening');
  return (
    <>
      <tr
        onClick={() => onOpen(result)}
        className={`border-b border-[var(--border)] transition-colors ${
          isExpanded ? 'bg-[var(--background)]' : 'hover:bg-[var(--background)]'
        } cursor-pointer`}
      >
        <td className="w-14 whitespace-nowrap px-3 py-3 text-center text-sm text-[var(--foreground-muted)]">
          {rank}
        </td>
        <td className="whitespace-nowrap px-3 py-3">
          <span className="font-mono text-sm font-medium text-[var(--color-primary)]">
            {result.ticker}
          </span>
        </td>
        <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--foreground)]">{result.name}</td>
        <td className="whitespace-nowrap px-3 py-3 text-center">
          {result.market ? (
            <span className="inline-flex rounded-full bg-[var(--background)] border border-[var(--border)] px-2 py-0.5 text-xs font-medium text-[var(--foreground-muted)]">
              {result.market}
            </span>
          ) : (
            <span className="text-[var(--foreground-muted)]">-</span>
          )}
        </td>
        <td className="whitespace-nowrap px-3 py-3 text-right font-mono text-sm text-[var(--foreground)]">
          {formatPrice(result.current_price)}
        </td>
        <td className={`whitespace-nowrap px-3 py-3 text-right font-mono text-sm ${changePctColor(result.change_pct)}`}>
          {formatChangePct(result.change_pct)}
        </td>
        <td className="whitespace-nowrap px-3 py-3 text-right font-mono text-sm text-[var(--foreground)]">
          {formatVolume(result.volume)}
        </td>
        <td className="whitespace-nowrap px-3 py-3 text-right font-mono text-sm">
          <ScoreBadge score={result.score} />
        </td>
        <td className="w-10 whitespace-nowrap px-2 py-3 text-center">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggle(result.ticker);
            }}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            aria-label={isExpanded ? t('hideDetails') : t('showDetails')}
            aria-expanded={isExpanded}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td
            colSpan={colCount}
            className="border-b border-[var(--border)] bg-[var(--background)] px-4 py-3"
          >
            <ConditionDetails conditions={result.conditions} ticker={result.ticker} />
          </td>
        </tr>
      )}
    </>
  );
}

function MobileCard({ result, rank, isExpanded, onToggle, onOpen }: RowProps) {
  const t = useTranslations('screening');
  return (
    <div className="p-4">
      <button
        type="button"
        onClick={() => onOpen(result)}
        className="flex w-full items-start justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--background)] text-[10px] font-bold text-[var(--foreground-muted)]">
            {rank}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-medium text-[var(--color-primary)]">
                {result.ticker}
              </span>
              {result.market && (
                <span className="rounded-full bg-[var(--background)] border border-[var(--border)] px-1.5 py-0.5 text-[10px] text-[var(--foreground-muted)]">
                  {result.market}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-sm text-[var(--foreground)]">{result.name}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-sm font-medium text-[var(--foreground)]">
            {formatPrice(result.current_price)}
          </p>
          <p className={`font-mono text-xs ${changePctColor(result.change_pct)}`}>
            {formatChangePct(result.change_pct)}
          </p>
        </div>
      </button>

      <div className="mt-2 flex items-center gap-3 text-xs text-[var(--foreground-muted)]">
        <span>{t('volume')}: {formatVolume(result.volume)}</span>
        <span>{t('score')}: <ScoreBadge score={result.score} /></span>
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
          <ConditionDetails conditions={result.conditions} ticker={result.ticker} />
        </div>
      )}
    </div>
  );
}

interface ResultDetailModalProps {
  result: ScreeningResult;
  onClose: () => void;
}

function ResultDetailModal({ result, onClose }: ResultDetailModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <button type="button" className="absolute inset-0" onClick={onClose} aria-label="Close" />
      <div className="relative z-10 max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] shadow-2xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
          <div>
            <p className="font-mono text-sm font-semibold text-[var(--color-primary)]">{result.ticker}</p>
            <p className="text-sm text-[var(--foreground)]">{result.name}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--background)] hover:text-[var(--foreground)]"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-3 overflow-y-auto p-4">
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="font-mono text-[var(--foreground)]">{formatPrice(result.current_price)}</span>
            <span className="inline-flex rounded-full bg-[var(--background)] border border-[var(--border)] px-2 py-0.5 text-[10px] text-[var(--foreground-muted)]">
              {result.market ?? '-'}
            </span>
            <ScoreBadge score={result.score} />
          </div>
          <ConditionDetails conditions={result.conditions} ticker={result.ticker} />
        </div>
      </div>
    </div>
  );
}
