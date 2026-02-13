'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Globe } from 'lucide-react';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';

function UniverseNode({ data, selected }: NodeProps) {
  const nodeData = data as unknown as StrategyNodeData;

  return (
    <div
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border px-4 py-3 min-w-[200px] transition-shadow ${
        selected
          ? 'border-[#1313ec] shadow-[0_0_0_1px_#1313ec] ring-1 ring-[#1313ec]/20'
          : 'border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:shadow-md'
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-semibold uppercase tracking-wider">
          <Globe className="h-3 w-3" />
          Input
        </span>
      </div>
      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
        Market Selection
      </div>
      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
        {nodeData.universe || 'KOSPI'} Composite
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-bottom-[7px] hover:!scale-125 !transition-transform"
      />
    </div>
  );
}

export default memo(UniverseNode);
