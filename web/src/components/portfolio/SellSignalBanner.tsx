'use client';

import { AlertTriangle, X } from 'lucide-react';
import type { SellSignal } from '@/lib/types';

interface SellSignalBannerProps {
  /** List of sell signals to display */
  signals: SellSignal[];
  /** Callback when banner is dismissed */
  onDismiss?: () => void;
}

/**
 * Format signal type for display
 */
function formatSignalType(type: SellSignal['signal_type']): string {
  const labels: Record<SellSignal['signal_type'], string> = {
    stop_loss: 'Stop Loss',
    take_profit: 'Take Profit',
    trailing_stop: 'Trailing Stop',
    manual: 'Manual',
  };
  return labels[type] || type;
}

/**
 * Banner component displaying sell signals as warnings
 */
export default function SellSignalBanner({ signals, onDismiss }: SellSignalBannerProps) {
  if (signals.length === 0) {
    return null;
  }

  return (
    <div
      className="rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950/50"
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400" />
        <div className="flex-1">
          <h3 className="font-semibold text-red-800 dark:text-red-200">
            Sell Signal Alert ({signals.length})
          </h3>
          <div className="mt-2 space-y-2">
            {signals.map((signal) => (
              <div
                key={`${signal.ticker}-${signal.signal_type}`}
                className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-red-700 dark:text-red-300"
              >
                <span className="font-mono font-medium">{signal.ticker}</span>
                {signal.name && (
                  <span className="text-red-600 dark:text-red-400">{signal.name}</span>
                )}
                <span className="rounded bg-red-200 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-800 dark:text-red-200">
                  {formatSignalType(signal.signal_type)}
                </span>
                <span className="text-red-600 dark:text-red-400">{signal.reason}</span>
              </div>
            ))}
          </div>
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="rounded p-1 text-red-600 hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/50 transition-colors"
            aria-label="Dismiss alert"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
