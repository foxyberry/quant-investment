'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Filter } from 'lucide-react';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import { getConditionMeta } from '@/lib/strategy/conditionRegistry';

function ConditionNode({ data, selected }: NodeProps) {
  const nodeData = data as unknown as StrategyNodeData;
  const meta = nodeData.condition_type
    ? getConditionMeta(nodeData.condition_type)
    : null;

  const label = meta?.label || nodeData.label || 'Condition';

  // Show key params as summary
  const paramSummary = nodeData.params
    ? Object.entries(nodeData.params)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => `${k}: ${v}`)
        .slice(0, 2)
        .join(', ')
    : '';

  return (
    <div
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border px-4 py-3 min-w-[200px] transition-shadow ${
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
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-500/10 text-[#1313ec] dark:text-blue-400 text-[10px] font-semibold uppercase tracking-wider">
          <Filter className="h-3 w-3" />
          Screening
        </span>
      </div>
      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
        {label}
      </div>
      {paramSummary && (
        <div className="flex items-center gap-1.5 mt-1.5">
          <span className="text-[11px] text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 px-1.5 py-0.5 rounded font-mono">
            {paramSummary}
          </span>
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-bottom-[7px] hover:!scale-125 !transition-transform"
      />
    </div>
  );
}

export default memo(ConditionNode);
