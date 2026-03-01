'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { X } from 'lucide-react';
import { useTranslations, useLocale } from 'next-intl';
import { Button } from '@/components/ui';
import { formatCurrency as formatCurrencyUtil } from '@/lib/format';
import type { Holding, HoldingUpdate, AdditionalPurchaseRequest } from '@/lib/types';

type EditMode = 'full' | 'add';

interface EditHoldingModalProps {
  isOpen: boolean;
  holding: Holding | null;
  onClose: () => void;
  onUpdate: (ticker: string, data: HoldingUpdate) => Promise<void>;
  onAddPurchase?: (ticker: string, data: AdditionalPurchaseRequest) => Promise<void>;
}

interface FormErrors {
  quantity?: string;
  avg_price?: string;
  add_quantity?: string;
  add_price?: string;
}

export default function EditHoldingModal({
  isOpen,
  holding,
  onClose,
  onUpdate,
  onAddPurchase,
}: EditHoldingModalProps) {
  const t = useTranslations('portfolio');
  const locale = useLocale();
  const formatCurrency = (value: number, currency?: string) =>
    formatCurrencyUtil(value, currency, locale);

  const [mode, setMode] = useState<EditMode>('full');

  // Full-edit fields
  const [quantity, setQuantity] = useState('');
  const [avgPrice, setAvgPrice] = useState('');

  // Add-purchase fields
  const [addQuantity, setAddQuantity] = useState('');
  const [addPrice, setAddPrice] = useState('');
  const [addFee, setAddFee] = useState('');
  const [addDate, setAddDate] = useState('');
  const [addNote, setAddNote] = useState('');

  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const quantityInputRef = useRef<HTMLInputElement>(null);
  const addQuantityInputRef = useRef<HTMLInputElement>(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen && holding) {
      setMode('full');
      setQuantity(holding.quantity.toString());
      setAvgPrice(holding.avg_price.toString());
      setAddQuantity('');
      setAddPrice('');
      setAddFee('');
      setAddDate('');
      setAddNote('');
      setErrors({});
      setSubmitError(null);
      setTimeout(() => quantityInputRef.current?.focus(), 100);
    }
  }, [isOpen, holding]);

  // Focus correct input on mode switch
  useEffect(() => {
    if (!isOpen) return;
    setTimeout(() => {
      if (mode === 'full') {
        quantityInputRef.current?.focus();
      } else {
        addQuantityInputRef.current?.focus();
      }
    }, 50);
  }, [mode, isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Preview calculation for add-purchase mode
  const preview = useMemo(() => {
    if (!holding || mode !== 'add') return null;
    const addQty = parseFloat(addQuantity);
    const addPrc = parseFloat(addPrice);
    if (!addQty || addQty <= 0 || !addPrc || addPrc <= 0) return null;

    const oldQty = holding.quantity;
    const oldAvg = holding.avg_price;
    const newQty = oldQty + addQty;
    const newAvg = (oldQty * oldAvg + addQty * addPrc) / newQty;

    return { oldQty, oldAvg, newQty, newAvg };
  }, [holding, mode, addQuantity, addPrice]);

  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (mode === 'full') {
      const qty = parseInt(quantity, 10);
      if (!quantity.trim()) {
        newErrors.quantity = t('quantityRequired');
      } else if (isNaN(qty) || qty <= 0 || !Number.isInteger(parseFloat(quantity))) {
        newErrors.quantity = t('quantityPositive');
      }

      const price = parseFloat(avgPrice);
      if (!avgPrice.trim()) {
        newErrors.avg_price = t('priceRequired');
      } else if (isNaN(price) || price <= 0) {
        newErrors.avg_price = t('pricePositive');
      }
    } else {
      const qty = parseInt(addQuantity, 10);
      if (!addQuantity.trim()) {
        newErrors.add_quantity = t('quantityRequired');
      } else if (isNaN(qty) || qty <= 0 || !Number.isInteger(parseFloat(addQuantity))) {
        newErrors.add_quantity = t('quantityPositive');
      }

      const price = parseFloat(addPrice);
      if (!addPrice.trim()) {
        newErrors.add_price = t('priceRequired');
      } else if (isNaN(price) || price <= 0) {
        newErrors.add_price = t('pricePositive');
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [mode, quantity, avgPrice, addQuantity, addPrice, t]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!holding || !validate()) return;

      setIsSubmitting(true);
      setSubmitError(null);

      try {
        if (mode === 'full') {
          await onUpdate(holding.ticker, {
            quantity: parseInt(quantity, 10),
            avg_price: parseFloat(avgPrice),
          });
        } else if (onAddPurchase) {
          const data: AdditionalPurchaseRequest = {
            quantity: parseInt(addQuantity, 10),
            price: parseFloat(addPrice),
          };
          const fee = parseFloat(addFee);
          if (!isNaN(fee) && fee >= 0) data.fee = fee;
          if (addDate.trim()) data.traded_at = addDate.trim();
          if (addNote.trim()) data.note = addNote.trim();

          await onAddPurchase(holding.ticker, data);
        }
        onClose();
      } catch (error) {
        setSubmitError(
          error instanceof Error ? error.message : 'Failed to update holding',
        );
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      holding,
      mode,
      quantity,
      avgPrice,
      addQuantity,
      addPrice,
      addFee,
      addDate,
      addNote,
      validate,
      onUpdate,
      onAddPurchase,
      onClose,
    ],
  );

  if (!isOpen || !holding) return null;

  const inputClass = (hasError: boolean) =>
    `w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
      hasError ? 'border-red-500' : 'border-[var(--border)]'
    }`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-holding-title"
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
          <div>
            <h2
              id="edit-holding-title"
              className="text-lg font-semibold text-[var(--foreground)]"
            >
              {t('editHolding')}
            </h2>
            <p className="text-sm text-[var(--foreground-muted)]">
              <span className="font-mono font-medium text-[var(--color-primary)]">
                {holding.ticker}
              </span>
              {holding.name && ` - ${holding.name}`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab toggle */}
        <div className="flex gap-1 rounded-lg bg-[var(--background)] p-1 mx-6 mt-4">
          <button
            type="button"
            onClick={() => setMode('full')}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              mode === 'full'
                ? 'bg-[var(--background-secondary)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {t('fullEdit')}
          </button>
          <button
            type="button"
            onClick={() => setMode('add')}
            disabled={!onAddPurchase}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              mode === 'add'
                ? 'bg-[var(--background-secondary)] text-[var(--foreground)] shadow-sm'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            } ${!onAddPurchase ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {t('additionalPurchase')}
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          {submitError && (
            <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
              {submitError}
            </div>
          )}

          {/* Full Edit Mode */}
          {mode === 'full' && (
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="edit-quantity"
                  className="block text-sm font-medium text-[var(--foreground)] mb-1"
                >
                  {t('quantity')} <span className="text-red-500">*</span>
                </label>
                <input
                  ref={quantityInputRef}
                  type="number"
                  id="edit-quantity"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder={t('quantityPlaceholder')}
                  step="1"
                  min="1"
                  className={inputClass(!!errors.quantity)}
                  disabled={isSubmitting}
                />
                {errors.quantity && (
                  <p className="mt-1 text-sm text-red-500">{errors.quantity}</p>
                )}
              </div>

              <div>
                <label
                  htmlFor="edit-avg_price"
                  className="block text-sm font-medium text-[var(--foreground)] mb-1"
                >
                  {t('avgPrice')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  id="edit-avg_price"
                  value={avgPrice}
                  onChange={(e) => setAvgPrice(e.target.value)}
                  placeholder={t('pricePlaceholder')}
                  step="any"
                  min="0"
                  className={inputClass(!!errors.avg_price)}
                  disabled={isSubmitting}
                />
                {errors.avg_price && (
                  <p className="mt-1 text-sm text-red-500">
                    {errors.avg_price}
                  </p>
                )}
              </div>

              {holding.current_price !== null && (
                <div className="rounded-lg bg-[var(--background)] p-3 text-sm">
                  <p className="text-[var(--foreground-muted)]">
                    {t('currentPrice')}
                  </p>
                  <p className="font-mono font-medium text-[var(--foreground)]">
                    {formatCurrency(holding.current_price, holding.currency)}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Additional Purchase Mode */}
          {mode === 'add' && (
            <div className="space-y-4">
              {/* Current holding info */}
              <div className="rounded-lg bg-[var(--background)] p-3 text-sm">
                <p className="text-[var(--foreground-muted)] mb-1">
                  {t('currentHolding')}
                </p>
                <p className="font-mono text-[var(--foreground)]">
                  {holding.quantity.toLocaleString()} {t('shares')} @{' '}
                  {formatCurrency(holding.avg_price, holding.currency)}
                </p>
              </div>

              <div>
                <label
                  htmlFor="add-quantity"
                  className="block text-sm font-medium text-[var(--foreground)] mb-1"
                >
                  {t('addQty')} <span className="text-red-500">*</span>
                </label>
                <input
                  ref={addQuantityInputRef}
                  type="number"
                  id="add-quantity"
                  value={addQuantity}
                  onChange={(e) => setAddQuantity(e.target.value)}
                  placeholder={t('quantityPlaceholder')}
                  step="1"
                  min="1"
                  className={inputClass(!!errors.add_quantity)}
                  disabled={isSubmitting}
                />
                {errors.add_quantity && (
                  <p className="mt-1 text-sm text-red-500">
                    {errors.add_quantity}
                  </p>
                )}
              </div>

              <div>
                <label
                  htmlFor="add-price"
                  className="block text-sm font-medium text-[var(--foreground)] mb-1"
                >
                  {t('addPrice')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  id="add-price"
                  value={addPrice}
                  onChange={(e) => setAddPrice(e.target.value)}
                  placeholder={t('pricePlaceholder')}
                  step="any"
                  min="0"
                  className={inputClass(!!errors.add_price)}
                  disabled={isSubmitting}
                />
                {errors.add_price && (
                  <p className="mt-1 text-sm text-red-500">
                    {errors.add_price}
                  </p>
                )}
              </div>

              <div>
                <label
                  htmlFor="add-fee"
                  className="block text-sm font-medium text-[var(--foreground)] mb-1"
                >
                  {t('fee')}
                </label>
                <input
                  type="number"
                  id="add-fee"
                  value={addFee}
                  onChange={(e) => setAddFee(e.target.value)}
                  placeholder="0"
                  step="any"
                  min="0"
                  className={inputClass(false)}
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <label
                  htmlFor="add-date"
                  className="block text-sm font-medium text-[var(--foreground)] mb-1"
                >
                  {t('tradeDate')}
                </label>
                <input
                  type="date"
                  id="add-date"
                  value={addDate}
                  onChange={(e) => setAddDate(e.target.value)}
                  className={inputClass(false)}
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <label
                  htmlFor="add-note"
                  className="block text-sm font-medium text-[var(--foreground)] mb-1"
                >
                  {t('tradeNote')}
                </label>
                <input
                  type="text"
                  id="add-note"
                  value={addNote}
                  onChange={(e) => setAddNote(e.target.value)}
                  placeholder={t('sellNote')}
                  className={inputClass(false)}
                  disabled={isSubmitting}
                />
              </div>

              {/* Preview */}
              {preview && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm dark:border-blue-800 dark:bg-blue-950/30">
                  <p className="font-medium text-blue-700 dark:text-blue-300 mb-1">
                    {t('preview')}
                  </p>
                  <p className="font-mono text-blue-600 dark:text-blue-400">
                    {preview.oldQty.toLocaleString()} @ {formatCurrency(preview.oldAvg, holding.currency)}
                    {' → '}
                    {preview.newQty.toLocaleString()} @ {formatCurrency(preview.newAvg, holding.currency)}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              {t('cancel')}
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              className="flex-1"
            >
              {mode === 'full' ? t('updateHolding') : t('addPurchaseSubmit')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
