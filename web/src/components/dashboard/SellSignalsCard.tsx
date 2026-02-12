'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui';
import { getSellSignals } from '@/lib/api';
import type { SellSignal } from '@/lib/types';
import { AlertTriangle, ShieldCheck, TrendingDown, Target, Activity } from 'lucide-react';

interface LoadingState {
  loading: boolean;
  error: string | null;
}

const signalTypeConfig: Record<string, { label: string; icon: typeof AlertTriangle; colorClass: string }> = {
  stop_loss: {
    label: 'Stop Loss',
    icon: TrendingDown,
    colorClass: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  },
  take_profit: {
    label: 'Take Profit',
    icon: Target,
    colorClass: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  },
  trailing_stop: {
    label: 'Trailing Stop',
    icon: Activity,
    colorClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  },
  manual: {
    label: 'Manual',
    icon: AlertTriangle,
    colorClass: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  },
};

/**
 * Displays active sell signals for portfolio positions
 */
export default function SellSignalsCard() {
  const [signals, setSignals] = useState<SellSignal[]>([]);
  const [state, setState] = useState<LoadingState>({ loading: true, error: null });

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const data = await getSellSignals();
        setSignals(data);
        setState({ loading: false, error: null });
      } catch (err) {
        setState({
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to load sell signals',
        });
      }
    };

    fetchSignals();
  }, []);

  const formatPrice = (price: number | null) => {
    if (price === null) return '--';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(price);
  };

  // Loading skeleton
  if (state.loading) {
    return (
      <Card title="Sell Signals">
        <div className="space-y-3 animate-pulse">
          <div className="h-12 rounded bg-[var(--border)]" />
          <div className="h-12 rounded bg-[var(--border)]" />
        </div>
      </Card>
    );
  }

  // Error state
  if (state.error) {
    return (
      <Card title="Sell Signals">
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <AlertTriangle className="h-5 w-5" />
          <span>Unable to load sell signals</span>
        </div>
        <p className="mt-2 text-sm text-red-500">{state.error}</p>
      </Card>
    );
  }

  // No signals - safe state
  if (signals.length === 0) {
    return (
      <Card title="Sell Signals">
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="mb-3 rounded-full bg-green-100 p-3 dark:bg-green-900">
            <ShieldCheck className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
          <p className="text-lg font-medium text-[var(--foreground)]">All Clear</p>
          <p className="mt-1 text-sm text-[var(--foreground-muted)]">
            No sell signals triggered
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Sell Signals" padding="none">
      <div className="divide-y divide-[var(--border)]">
        {/* Alert header */}
        <div className="flex items-center gap-2 bg-red-50 px-6 py-3 dark:bg-red-950">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
          <span className="font-medium text-red-800 dark:text-red-200">
            {signals.length} signal{signals.length > 1 ? 's' : ''} requiring attention
          </span>
        </div>

        {/* Signal list */}
        <div className="max-h-64 overflow-y-auto">
          {signals.map((signal, index) => {
            const config = signalTypeConfig[signal.signal_type] || signalTypeConfig.manual;
            const Icon = config.icon;

            return (
              <div
                key={`${signal.ticker}-${index}`}
                className="flex items-start gap-3 px-6 py-4 hover:bg-[var(--background)] transition-colors"
              >
                {/* Signal type badge */}
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${config.colorClass}`}>
                  <Icon className="h-3 w-3" />
                  {config.label}
                </span>

                {/* Signal details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[var(--foreground)]">
                      {signal.ticker}
                    </span>
                    {signal.name && (
                      <span className="truncate text-sm text-[var(--foreground-muted)]">
                        {signal.name}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-[var(--foreground-muted)]">
                    {signal.reason}
                  </p>
                  <div className="mt-1 flex gap-4 text-xs text-[var(--foreground-muted)]">
                    <span>Current: {formatPrice(signal.current_price)}</span>
                    {signal.trigger_price && (
                      <span>Trigger: {formatPrice(signal.trigger_price)}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}
