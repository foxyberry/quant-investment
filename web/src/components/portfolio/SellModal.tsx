'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { X } from 'lucide-react';
import { Button } from '@/components/ui';
import { recordSell } from '@/lib/api';
import type { Holding } from '@/lib/types';
import { formatCurrency as formatCurrencyUtil } from '@/lib/format';

interface SellModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** The holding to sell (null when modal is closed) */
  holding: Holding | null;
  /** Callback to close the modal */
  onClose: () => void;
  /** Callback when the sell is recorded successfully */
  onSellComplete: () => void;
}

interface FormErrors {
  quantity?: string;
  price?: string;
  fee?: string;
  tax?: string;
}

/**
 * Modal for recording a sell transaction against a holding.
 *
 * Pre-fills ticker (readonly) and displays holding context (name, qty owned,
 * avg price, current price). On submit it calls `recordSell()` and then
 * invokes `onSellComplete` so the parent can refresh its data.
 */
export default function SellModal({
  isOpen,
  holding,
  onClose,
  onSellComplete,
}: SellModalProps) {
  const t = useTranslations('portfolio');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency?: string) =>
    formatCurrencyUtil(value, currency, locale);

  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [fee, setFee] = useState('0');
  const [tax, setTax] = useState('0');
  const [tradedAt, setTradedAt] = useState('');
  const [note, setNote] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const quantityInputRef = useRef<HTMLInputElement>(null);

  // Reset form when modal opens or holding changes
  useEffect(() => {
    if (isOpen && holding) {
      setQuantity('');
      setPrice(
        holding.current_price !== null ? holding.current_price.toString() : '',
      );
      setFee('0');
      setTax('0');
      setTradedAt(new Date().toISOString().slice(0, 10));
      setNote('');
      setErrors({});
      setSubmitError(null);
      setTimeout(() => quantityInputRef.current?.focus(), 100);
    }
  }, [isOpen, holding]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Real-time estimated P&L preview
  const estimatedPnl = useMemo(() => {
    if (!holding) return null;
    const qty = parseFloat(quantity);
    const sellPrice = parseFloat(price);
    const sellFee = parseFloat(fee) || 0;
    const sellTax = parseFloat(tax) || 0;
    if (
      !Number.isFinite(qty) ||
      qty <= 0 ||
      !Number.isFinite(sellPrice) ||
      sellPrice <= 0
    ) {
      return null;
    }
    return (sellPrice - holding.avg_price) * qty - sellFee - sellTax;
  }, [quantity, price, fee, tax, holding]);

  const validate = useCallback((): boolean => {
    if (!holding) return false;
    const newErrors: FormErrors = {};

    const qty = parseFloat(quantity);
    if (!quantity.trim()) {
      newErrors.quantity = t('quantityRequired');
    } else if (isNaN(qty) || qty <= 0) {
      newErrors.quantity = t('quantityPositive');
    } else if (qty > holding.quantity) {
      newErrors.quantity = t('sellQuantityExceeds', {
        max: holding.quantity.toString(),
      });
    }

    const sellPrice = parseFloat(price);
    if (!price.trim()) {
      newErrors.price = t('sellPriceRequired');
    } else if (isNaN(sellPrice) || sellPrice <= 0) {
      newErrors.price = t('sellPriceRequired');
    }

    const sellFee = parseFloat(fee || '0');
    if (isNaN(sellFee) || sellFee < 0) {
      newErrors.fee = t('sellCostNonNegative');
    }

    const sellTax = parseFloat(tax || '0');
    if (isNaN(sellTax) || sellTax < 0) {
      newErrors.tax = t('sellCostNonNegative');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [quantity, price, fee, tax, holding, t]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!holding || !validate()) return;

      setIsSubmitting(true);
      setSubmitError(null);

      try {
        await recordSell({
          ticker: holding.ticker,
          quantity: parseFloat(quantity),
          price: parseFloat(price),
          fee: parseFloat(fee) || undefined,
          tax: parseFloat(tax) || undefined,
          traded_at: tradedAt,
          note: note.trim() || undefined,
        });
        onSellComplete();
        onClose();
      } catch (error) {
        setSubmitError(
          error instanceof Error ? error.message : 'Failed to record sell',
        );
      } finally {
        setIsSubmitting(false);
      }
    },
    [holding, quantity, price, fee, tax, tradedAt, note, validate, onSellComplete, onClose],
  );

  if (!isOpen || !holding) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sell-modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative w-full max-w-md rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <h2
            id="sell-modal-title"
            className="text-lg font-semibold text-[var(--foreground)]"
          >
            {t('sellTitle')}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Holding info banner */}
        <div className="border-b border-[var(--border)] bg-[var(--background)]/50 px-6 py-3">
          <p className="text-sm font-medium text-[var(--foreground)]">
            <span className="font-mono text-[var(--color-primary)]">
              {holding.ticker}
            </span>
            {holding.name && (
              <span className="text-[var(--foreground-muted)]">
                {' '}&mdash; {holding.name}
              </span>
            )}
          </p>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--foreground-muted)]">
            <span>
              {t('sellOwned')}: {holding.quantity}
            </span>
            <span>
              {t('sellAvgPrice')}: {formatCurrency(holding.avg_price, holding.currency)}
            </span>
            {holding.current_price !== null && (
              <span>
                {t('currentPrice')}: {formatCurrency(holding.current_price, holding.currency)}
              </span>
            )}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          {submitError && (
            <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
              {submitError}
            </div>
          )}

          <div className="space-y-4">
            {/* Quantity */}
            <div>
              <label
                htmlFor="sell-quantity"
                className="block text-sm font-medium text-[var(--foreground)] mb-1"
              >
                {t('sellQuantity')} <span className="text-red-500">*</span>
              </label>
              <input
                ref={quantityInputRef}
                type="number"
                id="sell-quantity"
                value={quantity}
                onChange={(e) => { setQuantity(e.target.value); setErrors(prev => ({ ...prev, quantity: undefined })); }}
                placeholder={t('quantityPlaceholder')}
                step="any"
                min="0"
                max={holding.quantity}
                className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
                  errors.quantity ? 'border-red-500' : 'border-[var(--border)]'
                }`}
                disabled={isSubmitting}
              />
              <p className="mt-1 text-xs text-[var(--foreground-muted)]">
                {t('sellMaxQuantity', { max: holding.quantity.toString() })}
              </p>
              {errors.quantity && (
                <p className="mt-1 text-sm text-red-500">{errors.quantity}</p>
              )}
            </div>

            {/* Sell Price */}
            <div>
              <label
                htmlFor="sell-price"
                className="block text-sm font-medium text-[var(--foreground)] mb-1"
              >
                {t('sellPrice')} <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                id="sell-price"
                value={price}
                onChange={(e) => { setPrice(e.target.value); setErrors(prev => ({ ...prev, price: undefined })); }}
                placeholder={t('pricePlaceholder')}
                step="any"
                min="0"
                className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
                  errors.price ? 'border-red-500' : 'border-[var(--border)]'
                }`}
                disabled={isSubmitting}
              />
              {errors.price && (
                <p className="mt-1 text-sm text-red-500">{errors.price}</p>
              )}
            </div>

            {/* Fee */}
            <div>
              <label
                htmlFor="sell-fee"
                className="block text-sm font-medium text-[var(--foreground)] mb-1"
              >
                {t('sellFee')}
              </label>
              <input
                type="number"
                id="sell-fee"
                value={fee}
                onChange={(e) => { setFee(e.target.value); setErrors(prev => ({ ...prev, fee: undefined })); }}
                step="any"
                min="0"
                className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
                  errors.fee ? 'border-red-500' : 'border-[var(--border)]'
                }`}
                disabled={isSubmitting}
              />
              {errors.fee && (
                <p className="mt-1 text-sm text-red-500">{errors.fee}</p>
              )}
            </div>

            {/* Tax */}
            <div>
              <label
                htmlFor="sell-tax"
                className="block text-sm font-medium text-[var(--foreground)] mb-1"
              >
                {t('sellTax')}
              </label>
              <input
                type="number"
                id="sell-tax"
                value={tax}
                onChange={(e) => { setTax(e.target.value); setErrors(prev => ({ ...prev, tax: undefined })); }}
                step="any"
                min="0"
                className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
                  errors.tax ? 'border-red-500' : 'border-[var(--border)]'
                }`}
                disabled={isSubmitting}
              />
              {errors.tax && (
                <p className="mt-1 text-sm text-red-500">{errors.tax}</p>
              )}
            </div>

            {/* Trade Date */}
            <div>
              <label
                htmlFor="sell-date"
                className="block text-sm font-medium text-[var(--foreground)] mb-1"
              >
                {t('sellDate')}
              </label>
              <input
                type="date"
                id="sell-date"
                value={tradedAt}
                onChange={(e) => setTradedAt(e.target.value)}
                className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-[var(--foreground)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                disabled={isSubmitting}
              />
            </div>

            {/* Note */}
            <div>
              <label
                htmlFor="sell-note"
                className="block text-sm font-medium text-[var(--foreground)] mb-1"
              >
                {t('sellNote')}
              </label>
              <textarea
                id="sell-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-none"
                disabled={isSubmitting}
              />
            </div>

            {/* Estimated P&L Preview */}
            {estimatedPnl !== null && (
              <div className="rounded-lg bg-[var(--background)] p-3">
                <p className="text-sm text-[var(--foreground-muted)]">
                  {t('sellEstimatedPnl')}
                </p>
                <p
                  className={`text-lg font-mono font-semibold ${
                    estimatedPnl >= 0
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {estimatedPnl >= 0 ? '+' : ''}
                  {formatCurrency(estimatedPnl, holding.currency)}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              {t('done')}
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? t('sellSubmitting') : t('sellSubmit')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
