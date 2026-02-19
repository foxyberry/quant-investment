'use client';

import { memo, useCallback } from 'react';
import { Handle, Position, useNodeId, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Flag } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import NodeEditPopup from './NodeEditPopup';

function OutputNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const nodeData = data as unknown as StrategyNodeData;
  const resultCount = nodeData.resultCount;
  const nodeId = useNodeId()!;
  const { deleteElements } = useReactFlow();

  const handleDelete = useCallback(() => {
    deleteElements({ nodes: [{ id: nodeId }] });
  }, [nodeId, deleteElements]);

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
        position={Position.Left}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[7px] hover:!scale-125 !transition-transform"
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

      {/* Inline info popup (read-only) */}
      <NodeEditPopup selected={!!selected} onDelete={handleDelete}>
        <div className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
          {t('outputInstruction')}
        </div>
        {resultCount !== undefined && resultCount !== null && (
          <div className="rounded-lg bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 p-3 text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {resultCount.toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {t('stockCount')}
            </div>
          </div>
        )}
      </NodeEditPopup>
    </div>
  );
}

export default memo(OutputNode);
