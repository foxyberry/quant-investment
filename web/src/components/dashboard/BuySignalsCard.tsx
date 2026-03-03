'use client';

import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Card } from '@/components/ui';
import { getBuySignals } from '@/lib/api';
import type { BuySignal } from '@/lib/types';
import { AlertTriangle, Target, BarChart3, Star } from 'lucide-react';
import { formatCurrency } from '@/lib/format';

interface LoadingState {
  loading: boolean;
  error: string | null;
}

export default function BuySignalsCard() {
  const t = useTranslations('dashboard');
  const locale = useLocale();
  const [signals, setSignals] = useState<BuySignal[]>([]);
  const [state, setState] = useState<LoadingState>({ loading: true, error: null });

  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const data = await getBuySignals();
        setSignals(data);
        setState({ loading: false, error: null });
      } catch (err) {
        setState({
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to load buy signals',
        });
      }
    };

    fetchSignals();
  }, []);

  const signalTypeConfig: Record<string, { labelKey: string; icon: typeof Target; colorClass: string }> = {
    target_price: {
      labelKey: 'targetPrice',
      icon: Target,
      colorClass: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    },
    rsi_oversold: {
      labelKey: 'rsiOversold',
      icon: BarChart3,
      colorClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    },
  };

  const formatPrice = (price: number | null, currency: string | null = 'USD') => {
    if (price === null) return '--';
    return formatCurrency(price, currency || 'USD', locale);
  };

  if (state.loading) {
    return (
      <Card title={t('buySignals')}>
        <div className="space-y-3 animate-pulse">
          <div className="h-12 rounded bg-[var(--border)]" />
          <div className="h-12 rounded bg-[var(--border)]" />
        </div>
      </Card>
    );
  }

  if (state.error) {
    return (
      <Card title={t('buySignals')}>
        <div className="flex items-center gap-2 text-[var(--foreground-muted)]">
          <AlertTriangle className="h-5 w-5" />
          <span>{t('unableToLoadBuySignals')}</span>
        </div>
        <p className="mt-2 text-sm text-red-500">{state.error}</p>
      </Card>
    );
  }

  if (signals.length === 0) {
    return (
      <Card title={t('buySignals')}>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="mb-3 rounded-full bg-blue-50 p-3 dark:bg-blue-900/20">
            <Star className="h-8 w-8 text-blue-500 dark:text-blue-400" />
          </div>
          <p className="text-lg font-medium text-[var(--foreground)]">{t('allClearBuy')}</p>
          <p className="mt-1 text-sm text-[var(--foreground-muted)]">
            {t('noBuySignals')}
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card title={t('buySignals')} padding="none">
      <div className="divide-y divide-[var(--border)]">
        <div className="flex items-center gap-2 bg-green-50 px-6 py-3 dark:bg-green-950">
          <Target className="h-5 w-5 text-green-600 dark:text-green-400" />
          <span className="font-medium text-green-800 dark:text-green-200">
            {t('buySignalsAttention', { count: signals.length })}
          </span>
        </div>

        <div className="max-h-64 overflow-y-auto">
          {signals.map((signal, index) => {
            const config = signalTypeConfig[signal.signal_type] || signalTypeConfig.target_price;
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
                    <span>{t('current', { price: formatPrice(signal.current_price, signal.currency) })}</span>
                    {signal.target_price && (
                      <span>{t('target', { price: formatPrice(signal.target_price, signal.currency) })}</span>
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
