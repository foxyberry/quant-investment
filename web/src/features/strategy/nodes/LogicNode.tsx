'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { GitMerge } from 'lucide-react';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';

const OPERATOR_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  and: { bg: 'bg-blue-50 dark:bg-blue-500/10', text: 'text-[#1313ec] dark:text-blue-400', label: 'AND' },
  or: { bg: 'bg-purple-50 dark:bg-purple-500/10', text: 'text-purple-600 dark:text-purple-400', label: 'OR' },
  not: { bg: 'bg-red-50 dark:bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: 'NOT' },
};

function LogicNode({ data, selected }: NodeProps) {
  const nodeData = data as unknown as StrategyNodeData;
  const op = (nodeData.logic_operator || 'and').toLowerCase();
  const style = OPERATOR_STYLES[op] || OPERATOR_STYLES.and;

  return (
    <div
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border px-5 py-3 min-w-[100px] text-center transition-shadow ${
        selected
          ? 'border-[#1313ec] shadow-[0_0_0_1px_#1313ec] ring-1 ring-[#1313ec]/20'
          : 'border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:shadow-md'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-5 !h-5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[10px] hover:!scale-125 !transition-transform"
      />
      <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full ${style.bg}`}>
        <GitMerge className={`h-3.5 w-3.5 ${style.text}`} />
        <span className={`text-sm font-bold ${style.text}`}>{style.label}</span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!w-5 !h-5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[10px] hover:!scale-125 !transition-transform"
      />
    </div>
  );
}

export default memo(LogicNode);
