'use client';

import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Card } from '@/components/ui';
import { getSellSignals } from '@/lib/api';
import type { SellSignal } from '@/lib/types';
import { AlertTriangle, ShieldCheck, TrendingDown, Target, Activity } from 'lucide-react';
import { formatCurrency } from '@/lib/format';

interface LoadingState {
  loading: boolean;
  error: string | null;
}

export default function SellSignalsCard() {
  const t = useTranslations('dashboard');
  const locale = useLocale();
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

  const signalTypeConfig: Record<string, { labelKey: string; icon: typeof AlertTriangle; colorClass: string }> = {
    stop_loss: {
      labelKey: 'stopLoss',
      icon: TrendingDown,
      colorClass: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    },
    take_profit: {
      labelKey: 'takeProfit',
      icon: Target,
      colorClass: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    },
    trailing_stop: {
      labelKey: 'trailingStop',
      icon: Activity,
      colorClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    },
    manual: {
      labelKey: 'manual',
      icon: AlertTriangle,
      colorClass: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    },
  };

  const formatPrice = (price: number | null) => {
    if (price === null) return '--';
    return formatCurrency(price, 'USD', locale);
  };

  if (state.loading) {
    return (
      <Card title={t('sellSignals')}>
        <div className="space-y-3 animate-pulse">
          <div className="h-12 rounded bg-[var(--border)]" />
          <div className="h-12 rounded bg-[var(--border)]" />
        </div>
      </Card>
    );
  }

  if (state.error) {
    return (
      <Card title={t('sellSignals')}>
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <AlertTriangle className="h-5 w-5" />
          <span>{t('unableToLoadSignals')}</span>
        </div>
        <p className="mt-2 text-sm text-red-500">{state.error}</p>
      </Card>
    );
  }

  if (signals.length === 0) {
    return (
      <Card title={t('sellSignals')}>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="mb-3 rounded-full bg-green-100 p-3 dark:bg-green-900">
            <ShieldCheck className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
          <p className="text-lg font-medium text-[var(--foreground)]">{t('allClear')}</p>
          <p className="mt-1 text-sm text-[var(--foreground-muted)]">
            {t('noSellSignals')}
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card title={t('sellSignals')} padding="none">
      <div className="divide-y divide-[var(--border)]">
        <div className="flex items-center gap-2 bg-red-50 px-6 py-3 dark:bg-red-950">
          <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
          <span className="font-medium text-red-800 dark:text-red-200">
            {t('signalsAttention', { count: signals.length })}
          </span>
        </div>

        <div className="max-h-64 overflow-y-auto">
          {signals.map((signal, index) => {
            const config = signalTypeConfig[signal.signal_type] || signalTypeConfig.manual;
            const Icon = config.icon;

            return (
              <div
                key={`${signal.ticker}-${index}`}
                className="flex items-start gap-3 px-6 py-4 hover:bg-[var(--background)] transition-colors"
              >
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${config.colorClass}`}>
                  <Icon className="h-3 w-3" />
                  {t(config.labelKey)}
                </span>

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
                    <span>{t('current', { price: formatPrice(signal.current_price) })}</span>
                    {signal.trigger_price && (
                      <span>{t('trigger', { price: formatPrice(signal.trigger_price) })}</span>
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
