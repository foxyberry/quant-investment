'use client';

import { useState, useEffect, useCallback } from 'react';
import { Archive, ArrowLeft, X, Trash2, RefreshCw, DollarSign } from 'lucide-react';
import { Button } from '@/components/ui';
import {
  listPortfolioArchives,
  createPortfolioArchive,
  getPortfolioArchive,
  deletePortfolioArchive,
} from '@/lib/api';
import type { ArchiveSummary, ArchiveDetailResponse, ArchiveItemResponse } from '@/lib/types';

interface ArchiveModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Called after a successful archive-and-clear so the parent can refresh holdings */
  onHoldingsCleared?: () => void;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatPrice(value: number, currency: string): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value);
}

function PnlBadge({ pnl }: { pnl: number | null | undefined }) {
  if (pnl == null) return <span className="text-[var(--foreground-muted)]">-</span>;
  const isPositive = pnl >= 0;
  return (
    <span
      className={`font-mono font-semibold ${
        isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
      }`}
    >
      {isPositive ? '+' : ''}
      {pnl.toFixed(2)}%
    </span>
  );
}

// ── List View ───────────────────────────────────────────────────────────────

interface ListViewProps {
  archives: ArchiveSummary[];
  isLoading: boolean;
  error: string | null;
  onCreate: (name: string, description?: string, clearAfter?: boolean) => Promise<void>;
  onSelect: (id: number) => void;
  onDelete: (id: number) => Promise<void>;
}

function ListView({ archives, isLoading, error, onCreate, onSelect, onDelete }: ListViewProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [clearAfter, setClearAfter] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setIsCreating(true);
    setCreateError(null);
    try {
      await onCreate(newName.trim(), newDesc.trim() || undefined, clearAfter);
      setNewName('');
      setNewDesc('');
      setClearAfter(false);
      setShowCreateForm(false);
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : '생성에 실패했습니다.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Create button / form */}
      {!showCreateForm ? (
        <Button variant="primary" onClick={() => setShowCreateForm(true)} className="self-start">
          <Archive className="h-4 w-4 mr-2" />
          아카이브 생성
        </Button>
      ) : (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-4 flex flex-col gap-3">
          <p className="text-sm font-medium text-[var(--foreground)]">새 아카이브</p>
          {createError && (
            <p className="text-sm text-red-600 dark:text-red-400">{createError}</p>
          )}
          <div className="flex flex-col gap-2">
            <input
              type="text"
              placeholder="아카이브 이름 (필수)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            />
            <input
              type="text"
              placeholder="설명 (선택)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="w-full rounded-md border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={clearAfter}
              onChange={(e) => setClearAfter(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border)] accent-[var(--color-primary)]"
            />
            <span className="text-sm text-[var(--foreground-muted)]">아카이브 후 현재 포트폴리오 비우기</span>
          </label>
          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={handleCreate}
              isLoading={isCreating}
              disabled={!newName.trim()}
              className="flex-1"
            >
              저장
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateForm(false);
                setCreateError(null);
                setNewName('');
                setNewDesc('');
                setClearAfter(false);
              }}
              disabled={isCreating}
              className="flex-1"
            >
              취소
            </Button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-[var(--foreground-muted)]" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && archives.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 gap-2 text-[var(--foreground-muted)]">
          <Archive className="h-10 w-10 opacity-30" />
          <p className="text-sm">저장된 아카이브가 없습니다.</p>
        </div>
      )}

      {/* List */}
      {!isLoading && archives.length > 0 && (
        <ul className="flex flex-col gap-2">
          {archives.map((a) => (
            <li
              key={a.id}
              className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--background)] px-4 py-3 hover:bg-[var(--background-secondary)] transition-colors"
            >
              <button
                type="button"
                className="flex-1 text-left"
                onClick={() => onSelect(a.id)}
              >
                <p className="font-medium text-[var(--foreground)]">{a.name}</p>
                {a.description && (
                  <p className="mt-0.5 text-xs text-[var(--foreground-muted)] truncate max-w-xs">{a.description}</p>
                )}
                <p className="mt-1 text-xs text-[var(--foreground-muted)]">
                  {formatDate(a.archived_at)} &middot; {a.total_holdings}개 종목
                </p>
              </button>
              <button
                type="button"
                aria-label="아카이브 삭제"
                onClick={() => handleDelete(a.id)}
                disabled={deletingId === a.id}
                className="ml-3 rounded p-1.5 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/40 dark:hover:text-red-400 transition-colors disabled:opacity-40"
              >
                {deletingId === a.id ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Detail View ─────────────────────────────────────────────────────────────

interface DetailViewProps {
  detail: ArchiveDetailResponse;
  onBack: () => void;
  onRefreshWithPrices: (withPrices: boolean) => Promise<void>;
}

function DetailView({ detail, onBack, onRefreshWithPrices }: DetailViewProps) {
  const [withPrices, setWithPrices] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const hasPriceData = detail.items.some((item) => item.current_price != null);

  const handleTogglePrices = async () => {
    const next = !withPrices;
    setWithPrices(next);
    setIsRefreshing(true);
    try {
      await onRefreshWithPrices(next);
    } finally {
      setIsRefreshing(false);
    }
  };

  const showPriceColumns = withPrices && hasPriceData;

  return (
    <div className="flex flex-col gap-4">
      {/* Back + toggle */}
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          목록으로
        </button>
        <button
          type="button"
          onClick={handleTogglePrices}
          disabled={isRefreshing}
          className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
            withPrices
              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
              : 'border border-[var(--border)] text-[var(--foreground-muted)] hover:bg-[var(--border)]'
          }`}
        >
          {isRefreshing ? (
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <DollarSign className="h-3.5 w-3.5" />
          )}
          현재가로 조회
        </button>
      </div>

      {/* Archive meta */}
      <div>
        <h3 className="text-base font-semibold text-[var(--foreground)]">{detail.name}</h3>
        {detail.description && (
          <p className="mt-0.5 text-sm text-[var(--foreground-muted)]">{detail.description}</p>
        )}
        <p className="mt-1 text-xs text-[var(--foreground-muted)]">
          {formatDate(detail.archived_at)} &middot; {detail.total_holdings}개 종목
        </p>
      </div>

      {/* Items table */}
      <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--background)]">
              <th className="px-3 py-2.5 text-left text-xs font-medium text-[var(--foreground-muted)]">티커</th>
              <th className="px-3 py-2.5 text-left text-xs font-medium text-[var(--foreground-muted)]">종목명</th>
              <th className="px-3 py-2.5 text-right text-xs font-medium text-[var(--foreground-muted)]">수량</th>
              <th className="px-3 py-2.5 text-right text-xs font-medium text-[var(--foreground-muted)]">매수가</th>
              {showPriceColumns && (
                <>
                  <th className="px-3 py-2.5 text-right text-xs font-medium text-[var(--foreground-muted)]">현재가</th>
                  <th className="px-3 py-2.5 text-right text-xs font-medium text-[var(--foreground-muted)]">수익률</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {detail.items.length === 0 && (
              <tr>
                <td
                  colSpan={showPriceColumns ? 6 : 4}
                  className="px-3 py-8 text-center text-[var(--foreground-muted)]"
                >
                  종목이 없습니다.
                </td>
              </tr>
            )}
            {detail.items.map((item: ArchiveItemResponse, idx: number) => (
              <tr
                key={`${item.ticker}-${idx}`}
                className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--background)] transition-colors"
              >
                <td className="px-3 py-2.5 font-mono font-medium text-[var(--foreground)]">
                  {item.ticker}
                </td>
                <td className="px-3 py-2.5 text-[var(--foreground-muted)] max-w-[160px] truncate">
                  {item.name ?? '-'}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-[var(--foreground)]">
                  {item.quantity.toLocaleString()}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-[var(--foreground)]">
                  {formatPrice(item.avg_price, item.currency)}
                </td>
                {showPriceColumns && (
                  <>
                    <td className="px-3 py-2.5 text-right font-mono text-[var(--foreground)]">
                      {item.current_price != null
                        ? formatPrice(item.current_price, item.currency)
                        : '-'}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <PnlBadge pnl={item.pnl_pct} />
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── ArchiveModal ────────────────────────────────────────────────────────────

/**
 * Modal for creating, listing, and inspecting portfolio archives (snapshots).
 */
export default function ArchiveModal({ open, onClose, onHoldingsCleared }: ArchiveModalProps) {
  const [archives, setArchives] = useState<ArchiveSummary[]>([]);
  const [detail, setDetail] = useState<ArchiveDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  // Load list when opening
  const loadList = useCallback(async () => {
    setIsLoading(true);
    setListError(null);
    try {
      const data = await listPortfolioArchives();
      setArchives(data);
    } catch (e) {
      setListError(e instanceof Error ? e.message : '목록을 불러오지 못했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      setDetail(null);
      loadList();
    }
  }, [open, loadList]);

  // Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  const handleCreate = useCallback(
    async (name: string, description?: string, clearAfter?: boolean) => {
      await createPortfolioArchive({ name, description, clear_after: clearAfter ?? false });
      await loadList();
      if (clearAfter) {
        onHoldingsCleared?.();
      }
    },
    [loadList],
  );

  const handleDelete = useCallback(
    async (id: number) => {
      await deletePortfolioArchive(id);
      setArchives((prev) => prev.filter((a) => a.id !== id));
    },
    [],
  );

  const handleSelect = useCallback(async (id: number) => {
    try {
      const data = await getPortfolioArchive(id, false);
      setDetail(data);
    } catch (e) {
      setListError(e instanceof Error ? e.message : '상세 정보를 불러오지 못했습니다.');
    }
  }, []);

  const handleRefreshWithPrices = useCallback(
    async (withPrices: boolean) => {
      if (!detail) return;
      const data = await getPortfolioArchive(detail.id, withPrices);
      setDetail(data);
    },
    [detail],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="archive-modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative flex flex-col w-full max-w-2xl max-h-[85vh] rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-blue-100 p-2 dark:bg-blue-900/50">
              <Archive className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <h2 id="archive-modal-title" className="text-lg font-semibold text-[var(--foreground)]">
              포트폴리오 아카이브
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            aria-label="닫기"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-6">
          {detail ? (
            <DetailView
              detail={detail}
              onBack={() => setDetail(null)}
              onRefreshWithPrices={handleRefreshWithPrices}
            />
          ) : (
            <ListView
              archives={archives}
              isLoading={isLoading}
              error={listError}
              onCreate={handleCreate}
              onSelect={handleSelect}
              onDelete={handleDelete}
            />
          )}
        </div>
      </div>
    </div>
  );
}
