'use client';

import { useTranslations } from 'next-intl';
import type { StrategyStatus } from '@/lib/api';

interface PipelineStep {
  key: StrategyStatus;
  done: boolean;
  active: boolean;
}

interface StrategyPipelineBadgeProps {
  status: StrategyStatus;
}

const PIPELINE_ORDER: StrategyStatus[] = [
  'draft',
  'backtested',
  'validated',
  'production',
];

/**
 * Compact pipeline stepper showing strategy lifecycle progress.
 * Renders inline as a small horizontal step indicator.
 */
export default function StrategyPipelineBadge({
  status,
}: StrategyPipelineBadgeProps) {
  const t = useTranslations('strategy');

  if (status === 'retired') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
        {t('strategyStatus.retired')}
      </span>
    );
  }

  const currentIdx = PIPELINE_ORDER.indexOf(status);

  const steps: PipelineStep[] = PIPELINE_ORDER.map((key, idx) => ({
    key,
    done: idx < currentIdx,
    active: idx === currentIdx,
  }));

  return (
    <div className="flex items-center gap-0.5">
      {steps.map((step, idx) => (
        <div key={step.key} className="flex items-center">
          {idx > 0 && (
            <div
              className={`w-3 h-px mx-0.5 ${
                step.done
                  ? 'bg-green-400 dark:bg-green-500'
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
            />
          )}
          <div
            className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium leading-none ${
              step.done
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                : step.active
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 ring-1 ring-blue-300 dark:ring-blue-700'
                  : 'bg-gray-50 text-gray-400 dark:bg-gray-800/50 dark:text-gray-500'
            }`}
            title={t(`strategyStatus.${step.key}` as Parameters<typeof t>[0])}
          >
            {step.done && (
              <svg className="w-2.5 h-2.5" viewBox="0 0 12 12" fill="none">
                <path
                  d="M2.5 6L5 8.5L9.5 3.5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            {t(`strategyStatus.${step.key}` as Parameters<typeof t>[0])}
          </div>
        </div>
      ))}
    </div>
  );
}
