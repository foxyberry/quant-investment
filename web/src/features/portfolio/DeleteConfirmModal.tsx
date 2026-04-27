'use client';

import { useState, useCallback, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Button } from '@/components/ui';
import type { Holding } from '@/lib/types';

interface DeleteConfirmModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** The holding to delete */
  holding: Holding | null;
  /** Callback to close the modal */
  onClose: () => void;
  /** Callback when deletion is confirmed */
  onConfirm: (ticker: string) => Promise<void>;
}

/**
 * Modal for confirming holding deletion
 */
export default function DeleteConfirmModal({ isOpen, holding, onClose, onConfirm }: DeleteConfirmModalProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setDeleteError(null);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isDeleting) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, isDeleting, onClose]);

  const handleConfirm = useCallback(async () => {
    if (!holding) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await onConfirm(holding.ticker);
      onClose();
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : 'Failed to delete holding');
    } finally {
      setIsDeleting(false);
    }
  }, [holding, onConfirm, onClose]);

  if (!isOpen || !holding) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-confirm-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={isDeleting ? undefined : onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative w-full max-w-md rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-red-100 p-2 dark:bg-red-900/50">
              <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <h2 id="delete-confirm-title" className="text-lg font-semibold text-[var(--foreground)]">
              Delete Holding
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors disabled:opacity-50"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {deleteError && (
            <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
              {deleteError}
            </div>
          )}

          <p className="text-[var(--foreground)]">
            Are you sure you want to delete{' '}
            <span className="font-mono font-semibold text-[var(--color-primary)]">{holding.ticker}</span>
            {holding.name && <span className="text-[var(--foreground-muted)]"> ({holding.name})</span>}
            {' '}from your portfolio?
          </p>

          {/* Holding details */}
          <div className="mt-4 rounded-lg bg-[var(--background)] p-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-[var(--foreground-muted)]">Quantity</p>
                <p className="font-mono font-medium text-[var(--foreground)]">
                  {holding.quantity.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-[var(--foreground-muted)]">Market Value</p>
                <p className="font-mono font-medium text-[var(--foreground)]">
                  {holding.market_value !== null
                    ? new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: holding.currency,
                      }).format(holding.market_value)
                    : '-'}
                </p>
              </div>
            </div>
          </div>

          <p className="mt-4 text-sm text-[var(--foreground-muted)]">
            This action cannot be undone.
          </p>

          {/* Actions */}
          <div className="mt-6 flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isDeleting}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={handleConfirm}
              isLoading={isDeleting}
              className="flex-1 !bg-red-600 hover:!bg-red-700 focus:!ring-red-600"
            >
              Delete
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
