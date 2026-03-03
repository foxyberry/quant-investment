'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Plus, RefreshCw, Star, Trash2, Edit3, Shield, TrendingDown, TrendingUp } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import TickerSearchInput from '@/components/ui/TickerSearchInput';
import {
  getWatchlistItems,
  createWatchlistItem,
  updateWatchlistItem,
  deleteWatchlistItem,
  getTickerPrice,
} from '@/lib/api';
import type { WatchlistItem, WatchlistItemCreate, WatchlistItemUpdate } from '@/lib/types';
import { formatCurrency } from '@/lib/format';
import BuyRuleModal from '@/components/watchlist/BuyRuleModal';

export default function WatchlistPage() {
  const t = useTranslations('watchlist');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const openPopup = useCallback((ticker: string) => {
    const width = 900;
    const height = 700;
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;
    window.open(
      `/${locale}/analysis/${encodeURIComponent(ticker)}?popup=true`,
      `analysis_${ticker}`,
      `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
    );
  }, [locale]);
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editTarget, setEditTarget] = useState<WatchlistItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<WatchlistItem | null>(null);
  const [buyRuleTarget, setBuyRuleTarget] = useState<WatchlistItem | null>(null);

  // Add form state
  const [addForm, setAddForm] = useState({ ticker: '', name: '', target_price: '', note: '', tags: '' });
  const [addError, setAddError] = useState<string | null>(null);
  const [addSubmitting, setAddSubmitting] = useState(false);

  // Edit form state
  const [editForm, setEditForm] = useState({ name: '', target_price: '', note: '', tags: '' });
  const [editSubmitting, setEditSubmitting] = useState(false);

  const fetchItems = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const data = await getWatchlistItems();
      setItems(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watchlist');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleAdd = async () => {
    if (!addForm.ticker.trim()) {
      setAddError(t('tickerRequired'));
      return;
    }
    setAddSubmitting(true);
    setAddError(null);
    try {
      const data: WatchlistItemCreate = {
        ticker: addForm.ticker.trim().toUpperCase(),
        name: addForm.name.trim() || undefined,
        target_price: addForm.target_price ? parseFloat(addForm.target_price) : undefined,
        note: addForm.note.trim() || undefined,
        tags: addForm.tags.trim() ? addForm.tags.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      };
      await createWatchlistItem(data);
      setShowAddModal(false);
      setAddForm({ ticker: '', name: '', target_price: '', note: '', tags: '' });
      fetchItems();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to add item');
    } finally {
      setAddSubmitting(false);
    }
  };

  const handleEdit = async () => {
    if (!editTarget) return;
    setEditSubmitting(true);
    try {
      const data: WatchlistItemUpdate = {
        name: editForm.name.trim() || undefined,
        target_price: editForm.target_price ? parseFloat(editForm.target_price) : null,
        note: editForm.note.trim() || undefined,
        tags: editForm.tags.trim() ? editForm.tags.split(',').map(s => s.trim()).filter(Boolean) : undefined,
      };
      await updateWatchlistItem(editTarget.id, data);
      setEditTarget(null);
      fetchItems();
    } catch {
      // Error handled silently
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteWatchlistItem(deleteTarget.id);
      setDeleteTarget(null);
      fetchItems();
    } catch {
      // Error handled silently
    }
  };

  const openEdit = (item: WatchlistItem) => {
    setEditForm({
      name: item.name || '',
      target_price: item.target_price?.toString() || '',
      note: item.note || '',
      tags: item.tags?.join(', ') || '',
    });
    setEditTarget(item);
  };

  const formatPrice = (price: number | null, currency: string | null) => {
    if (price === null) return '--';
    return formatCurrency(price, currency || 'USD', locale);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[var(--foreground)]">{t('title')}</h1>
            <p className="text-[var(--foreground-muted)] mt-1">{t('subtitle')}</p>
          </div>
        </div>
        <Card>
          <div className="space-y-3 animate-pulse">
            <div className="h-12 rounded bg-[var(--border)]" />
            <div className="h-12 rounded bg-[var(--border)]" />
            <div className="h-12 rounded bg-[var(--border)]" />
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">{t('title')}</h1>
          <p className="text-[var(--foreground-muted)] mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => fetchItems(true)}
            variant="secondary"
            size="sm"
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={() => setShowAddModal(true)} size="sm">
            <Plus className="h-4 w-4 mr-1" />
            {t('addItem')}
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <Card>
          <p className="text-red-500">{error}</p>
        </Card>
      )}

      {/* Empty state */}
      {items.length === 0 && !error && (
        <Card>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-4 rounded-full bg-blue-50 p-4 dark:bg-blue-900/20">
              <Star className="h-10 w-10 text-blue-500" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--foreground)]">{t('noItems')}</h3>
            <p className="mt-2 text-sm text-[var(--foreground-muted)] max-w-md">
              {t('addFirstItem')}
            </p>
            <Button onClick={() => setShowAddModal(true)} className="mt-4">
              <Plus className="h-4 w-4 mr-1" />
              {t('addItem')}
            </Button>
          </div>
        </Card>
      )}

      {/* Watchlist Table */}
      {items.length > 0 && (
        <Card padding="none">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--background-secondary)]">
                  <th className="px-4 py-3 text-left font-medium text-[var(--foreground-muted)]">{t('ticker')}</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--foreground-muted)]">{t('name')}</th>
                  <th className="px-4 py-3 text-right font-medium text-[var(--foreground-muted)]">{t('currentPrice')}</th>
                  <th className="px-4 py-3 text-right font-medium text-[var(--foreground-muted)]">{t('changePct')}</th>
                  <th className="px-4 py-3 text-right font-medium text-[var(--foreground-muted)]">{t('targetPrice')}</th>
                  <th className="px-4 py-3 text-center font-medium text-[var(--foreground-muted)]">{t('rules')}</th>
                  <th className="px-4 py-3 text-right font-medium text-[var(--foreground-muted)]">{t('actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {items.map((item) => {
                  const changePct = item.change_pct;
                  const isUp = changePct !== null && changePct > 0;
                  const isDown = changePct !== null && changePct < 0;
                  const atTarget = item.target_price !== null && item.current_price !== null && item.current_price <= item.target_price;

                  return (
                    <tr key={item.id} className="hover:bg-[var(--background)] transition-colors">
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); openPopup(item.ticker); }}
                          className="font-semibold text-[#1313ec] dark:text-blue-400 hover:underline cursor-pointer"
                        >
                          {item.ticker}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-[var(--foreground-muted)]">
                        {item.name || '--'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-[var(--foreground)]">
                        {formatPrice(item.current_price, item.currency)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {changePct !== null ? (
                          <span className={`inline-flex items-center gap-0.5 font-mono ${isUp ? 'text-green-600 dark:text-green-400' : isDown ? 'text-red-600 dark:text-red-400' : 'text-[var(--foreground-muted)]'}`}>
                            {isUp && <TrendingUp className="h-3 w-3" />}
                            {isDown && <TrendingDown className="h-3 w-3" />}
                            {changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%
                          </span>
                        ) : '--'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {item.target_price !== null ? (
                          <span className={`font-mono ${atTarget ? 'text-green-600 dark:text-green-400 font-semibold' : 'text-[var(--foreground-muted)]'}`}>
                            {formatPrice(item.target_price, item.currency)}
                          </span>
                        ) : '--'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                          {item.buy_rules_count}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => setBuyRuleTarget(item)}
                            className="rounded-md p-1.5 text-[var(--foreground-muted)] hover:bg-purple-100 hover:text-purple-600 dark:hover:bg-purple-900/30 dark:hover:text-purple-400 transition-colors"
                            title={t('buyRules')}
                          >
                            <Shield className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => openEdit(item)}
                            className="rounded-md p-1.5 text-[var(--foreground-muted)] hover:bg-blue-100 hover:text-blue-600 dark:hover:bg-blue-900/30 dark:hover:text-blue-400 transition-colors"
                            title={t('editItem')}
                          >
                            <Edit3 className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(item)}
                            className="rounded-md p-1.5 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
                            title={t('removeItem')}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowAddModal(false)}>
          <div className="mx-4 w-full max-w-md rounded-xl bg-[var(--background-secondary)] p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">{t('addToWatchlist')}</h2>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('ticker')}</label>
                <TickerSearchInput
                  value={addForm.ticker}
                  onChange={(ticker, name) => {
                    setAddForm((prev) => ({ ...prev, ticker, name: name || prev.name }));
                    // Auto-fill target price with current price on ticker selection
                    if (ticker && /^[A-Za-z0-9.^-]+$/.test(ticker)) {
                      getTickerPrice(ticker)
                        .then(({ price }) => {
                          if (price != null) {
                            setAddForm((prev) => prev.ticker === ticker
                              ? { ...prev, target_price: String(price) }
                              : prev
                            );
                          }
                        })
                        .catch(() => {});
                    }
                  }}
                  placeholder={t('tickerPlaceholder') + ' / 삼성전자'}
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('name')}</label>
                <input
                  type="text"
                  value={addForm.name}
                  onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                  placeholder={t('namePlaceholder')}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('targetPrice')}</label>
                <input
                  type="number"
                  value={addForm.target_price}
                  onChange={(e) => setAddForm({ ...addForm, target_price: e.target.value })}
                  placeholder={t('targetPricePlaceholder')}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                  step="any"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('note')}</label>
                <textarea
                  value={addForm.note}
                  onChange={(e) => setAddForm({ ...addForm, note: e.target.value })}
                  placeholder={t('notePlaceholder')}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] resize-none"
                  rows={2}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('tags')}</label>
                <input
                  type="text"
                  value={addForm.tags}
                  onChange={(e) => setAddForm({ ...addForm, tags: e.target.value })}
                  placeholder={t('tagsPlaceholder')}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </div>
            </div>

            {addError && <p className="mt-2 text-sm text-red-500">{addError}</p>}

            <div className="mt-6 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setShowAddModal(false)}>{tCommon('cancel')}</Button>
              <Button onClick={handleAdd} disabled={addSubmitting}>
                {addSubmitting ? '...' : t('addToWatchlist')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setEditTarget(null)}>
          <div className="mx-4 w-full max-w-md rounded-xl bg-[var(--background-secondary)] p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
              {t('editItem')} - {editTarget.ticker}
            </h2>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('name')}</label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('targetPrice')}</label>
                <input
                  type="number"
                  value={editForm.target_price}
                  onChange={(e) => setEditForm({ ...editForm, target_price: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                  step="any"
                  min="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('note')}</label>
                <textarea
                  value={editForm.note}
                  onChange={(e) => setEditForm({ ...editForm, note: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] resize-none"
                  rows={2}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">{t('tags')}</label>
                <input
                  type="text"
                  value={editForm.tags}
                  onChange={(e) => setEditForm({ ...editForm, tags: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditTarget(null)}>{tCommon('cancel')}</Button>
              <Button onClick={handleEdit} disabled={editSubmitting}>
                {editSubmitting ? '...' : t('updateItem')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setDeleteTarget(null)}>
          <div className="mx-4 w-full max-w-sm rounded-xl bg-[var(--background-secondary)] p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-[var(--foreground)] mb-2">
              {t('confirmRemove', { ticker: deleteTarget.ticker })}
            </h2>
            <p className="text-sm text-[var(--foreground-muted)]">{t('confirmRemoveDesc')}</p>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteTarget(null)}>{tCommon('cancel')}</Button>
              <button
                type="button"
                onClick={handleDelete}
                className="inline-flex items-center justify-center rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
              >
                {t('removeItem')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Buy Rule Modal */}
      {buyRuleTarget && (
        <BuyRuleModal
          item={buyRuleTarget}
          onClose={() => setBuyRuleTarget(null)}
          onUpdate={() => fetchItems()}
        />
      )}
    </div>
  );
}
