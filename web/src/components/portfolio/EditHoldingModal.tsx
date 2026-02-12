'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui';
import type { Holding, HoldingUpdate } from '@/lib/types';

interface EditHoldingModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** The holding to edit */
  holding: Holding | null;
  /** Callback to close the modal */
  onClose: () => void;
  /** Callback when holding is successfully updated */
  onUpdate: (ticker: string, data: HoldingUpdate) => Promise<void>;
}

interface FormErrors {
  quantity?: string;
  avg_price?: string;
}

/**
 * Modal for editing an existing holding
 */
export default function EditHoldingModal({ isOpen, holding, onClose, onUpdate }: EditHoldingModalProps) {
  const [quantity, setQuantity] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const quantityInputRef = useRef<HTMLInputElement>(null);

  // Populate form when holding changes
  useEffect(() => {
    if (isOpen && holding) {
      setQuantity(holding.quantity.toString());
      setAvgPrice(holding.avg_price.toString());
      setErrors({});
      setSubmitError(null);
      // Focus quantity input after a short delay
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

  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

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
  }, [quantity, avgPrice]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!holding || !validate()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await onUpdate(holding.ticker, {
        quantity: parseFloat(quantity),
        avg_price: parseFloat(avgPrice),
      });
      onClose();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to update holding');
    } finally {
      setIsSubmitting(false);
    }
  }, [holding, quantity, avgPrice, validate, onUpdate, onClose]);

  if (!isOpen || !holding) return null;

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
            <h2 id="edit-holding-title" className="text-lg font-semibold text-[var(--foreground)]">
              Edit Holding
            </h2>
            <p className="text-sm text-[var(--foreground-muted)]">
              <span className="font-mono font-medium text-[var(--color-primary)]">{holding.ticker}</span>
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
              <label htmlFor="edit-quantity" className="block text-sm font-medium text-[var(--foreground)] mb-1">
                Quantity <span className="text-red-500">*</span>
              </label>
              <input
                ref={quantityInputRef}
                type="number"
                id="edit-quantity"
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
              <label htmlFor="edit-avg_price" className="block text-sm font-medium text-[var(--foreground)] mb-1">
                Average Price <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                id="edit-avg_price"
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

            {/* Current price info (read-only) */}
            {holding.current_price !== null && (
              <div className="rounded-lg bg-[var(--background)] p-3 text-sm">
                <p className="text-[var(--foreground-muted)]">Current Price</p>
                <p className="font-mono font-medium text-[var(--foreground)]">
                  {new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: holding.currency,
                  }).format(holding.current_price)}
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
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              className="flex-1"
            >
              Update Holding
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
