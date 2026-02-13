'use client';

import type { BacktestMetrics } from '@/lib/api';

interface MetricsCardsProps {
  metrics: BacktestMetrics;
}

interface MetricCardDef {
  label: string;
  key: keyof BacktestMetrics;
  format: (v: number) => string;
  colorMode: 'pnl' | 'neutral';
}

const METRIC_CARDS: MetricCardDef[] = [
  {
    label: 'Total Return',
    key: 'total_return',
    format: (v) => `${(v * 100).toFixed(2)}%`,
    colorMode: 'pnl',
  },
  {
    label: 'Sharpe Ratio',
    key: 'sharpe_ratio',
    format: (v) => v.toFixed(2),
    colorMode: 'pnl',
  },
  {
    label: 'Max Drawdown',
    key: 'max_drawdown',
    format: (v) => `${(v * 100).toFixed(2)}%`,
    colorMode: 'pnl',
  },
  {
    label: 'Win Rate',
    key: 'win_rate',
    format: (v) => `${(v * 100).toFixed(1)}%`,
    colorMode: 'neutral',
  },
  {
    label: 'CAGR',
    key: 'cagr',
    format: (v) => `${(v * 100).toFixed(2)}%`,
    colorMode: 'pnl',
  },
  {
    label: 'Profit Factor',
    key: 'profit_factor',
    format: (v) => v.toFixed(2),
    colorMode: 'pnl',
  },
];

function getValueColor(value: number, mode: 'pnl' | 'neutral'): string {
  if (mode === 'neutral') {
    return 'text-[#1313ec] dark:text-blue-400';
  }
  if (value > 0) return 'text-emerald-600 dark:text-emerald-400';
  if (value < 0) return 'text-red-600 dark:text-red-400';
  return 'text-gray-700 dark:text-gray-200';
}

export default function MetricsCards({ metrics }: MetricsCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {METRIC_CARDS.map((card) => {
        const value = metrics[card.key];
        return (
          <div
            key={card.key}
            className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] p-3 shadow-sm"
          >
            <div className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1">
              {card.label}
            </div>
            <div
              className={`text-lg font-bold ${getValueColor(value, card.colorMode)}`}
            >
              {card.format(value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
