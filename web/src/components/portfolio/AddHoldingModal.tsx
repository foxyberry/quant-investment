'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui';
import type { HoldingCreate } from '@/lib/types';

interface AddHoldingModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Callback when holding is successfully added */
  onAdd: (data: HoldingCreate) => Promise<void>;
}

interface FormErrors {
  ticker?: string;
  quantity?: string;
  avg_price?: string;
}

/**
 * Modal for adding a new holding to the portfolio
 */
export default function AddHoldingModal({ isOpen, onClose, onAdd }: AddHoldingModalProps) {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const tickerInputRef = useRef<HTMLInputElement>(null);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setTicker('');
      setQuantity('');
      setAvgPrice('');
      setCurrency('USD');
      setErrors({});
      setSubmitError(null);
      // Focus ticker input after a short delay
      setTimeout(() => tickerInputRef.current?.focus(), 100);
    }
  }, [isOpen]);

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

  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!ticker.trim()) {
      newErrors.ticker = 'Ticker is required';
    } else if (!/^[A-Za-z0-9.-]+$/.test(ticker.trim())) {
      newErrors.ticker = 'Invalid ticker format';
    }

    const qty = parseFloat(quantity);
    if (!quantity.trim()) {
      newErrors.quantity = 'Quantity is required';
    } else if (isNaN(qty) || qty <= 0) {
      newErrors.quantity = 'Quantity must be a positive number';
    }

    const price = parseFloat(avgPrice);
    if (!avgPrice.trim()) {
      newErrors.avg_price = 'Average price is required';
    } else if (isNaN(price) || price <= 0) {
      newErrors.avg_price = 'Price must be a positive number';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [ticker, quantity, avgPrice]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await onAdd({
        ticker: ticker.trim().toUpperCase(),
        quantity: parseFloat(quantity),
        avg_price: parseFloat(avgPrice),
        currency,
      });
      onClose();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to add holding');
    } finally {
      setIsSubmitting(false);
    }
  }, [ticker, quantity, avgPrice, currency, validate, onAdd, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-holding-title"
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
          <h2 id="add-holding-title" className="text-lg font-semibold text-[var(--foreground)]">
            Add Holding
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

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          {submitError && (
            <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
              {submitError}
            </div>
          )}

          <div className="space-y-4">
            {/* Ticker */}
            <div>
              <label htmlFor="ticker" className="block text-sm font-medium text-[var(--foreground)] mb-1">
                Ticker <span className="text-red-500">*</span>
              </label>
              <input
                ref={tickerInputRef}
                type="text"
                id="ticker"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="e.g., AAPL"
                className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
                  errors.ticker ? 'border-red-500' : 'border-[var(--border)]'
                }`}
                disabled={isSubmitting}
              />
              {errors.ticker && (
                <p className="mt-1 text-sm text-red-500">{errors.ticker}</p>
              )}
            </div>

            {/* Quantity */}
            <div>
              <label htmlFor="quantity" className="block text-sm font-medium text-[var(--foreground)] mb-1">
                Quantity <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                id="quantity"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="e.g., 100"
                step="any"
                min="0"
                className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
                  errors.quantity ? 'border-red-500' : 'border-[var(--border)]'
                }`}
                disabled={isSubmitting}
              />
              {errors.quantity && (
                <p className="mt-1 text-sm text-red-500">{errors.quantity}</p>
              )}
            </div>

            {/* Average Price */}
            <div>
              <label htmlFor="avg_price" className="block text-sm font-medium text-[var(--foreground)] mb-1">
                Average Price <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                id="avg_price"
                value={avgPrice}
                onChange={(e) => setAvgPrice(e.target.value)}
                placeholder="e.g., 150.00"
                step="any"
                min="0"
                className={`w-full rounded-lg border px-3 py-2 text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] ${
                  errors.avg_price ? 'border-red-500' : 'border-[var(--border)]'
                }`}
                disabled={isSubmitting}
              />
              {errors.avg_price && (
                <p className="mt-1 text-sm text-red-500">{errors.avg_price}</p>
              )}
            </div>

            {/* Currency */}
            <div>
              <label htmlFor="currency" className="block text-sm font-medium text-[var(--foreground)] mb-1">
                Currency
              </label>
              <select
                id="currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-[var(--foreground)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                disabled={isSubmitting}
              >
                <option value="USD">USD</option>
                <option value="KRW">KRW</option>
                <option value="EUR">EUR</option>
                <option value="JPY">JPY</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
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
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              className="flex-1"
            >
              Add Holding
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
