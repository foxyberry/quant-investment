'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Flag } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';

function OutputNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const nodeData = data as unknown as StrategyNodeData;
  const resultCount = nodeData.resultCount;

  return (
    <div
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border px-4 py-3 min-w-[180px] text-center transition-shadow ${
        selected
          ? 'border-[#1313ec] shadow-[0_0_0_1px_#1313ec] ring-1 ring-[#1313ec]/20'
          : 'border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:shadow-md'
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-top-[7px] hover:!scale-125 !transition-transform"
      />
      <div className="flex items-center justify-center gap-2 mb-1">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 text-[10px] font-semibold uppercase tracking-wider">
          <Flag className="h-3 w-3" />
          {t('outputBadge')}
        </span>
      </div>
      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
        {t('finalSelection')}
      </div>
      {resultCount !== undefined && resultCount !== null ? (
        <div className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
          {t('estimatedItems', { count: resultCount })}
        </div>
      ) : (
        <div className="mt-1 text-xs text-gray-400 dark:text-gray-500">
          {t('connectAndRun')}
        </div>
      )}
    </div>
  );
}

export default memo(OutputNode);
