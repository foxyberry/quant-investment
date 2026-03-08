'use client';

import { memo, useCallback } from 'react';
import { Handle, Position, useNodeId, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Flag, Eye } from 'lucide-react';
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
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border min-w-[180px] transition-shadow ${
        selected
          ? 'border-2 border-[#1313ec] shadow-xl'
          : 'border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:shadow-md'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[7px] hover:!scale-125 !transition-transform"
      />
      {/* Header bar */}
      <div className="px-3 py-2 border-b border-[#e1e3e5] dark:border-[#2e2e30] bg-[#1313ec]/5 rounded-t-[7px] flex items-center gap-2">
        <Flag className="h-3.5 w-3.5 text-[#1313ec] dark:text-blue-400" />
        <span className="text-[11px] font-bold text-[#1313ec] dark:text-blue-400 uppercase tracking-wider">
          {t('outputBadge')}
        </span>
      </div>
      {/* Content */}
      <div className="p-3">
        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {t('finalSelection')}
        </div>
        {resultCount !== undefined && resultCount !== null ? (
          <div className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
            {t('estimatedItems', { count: resultCount })}
          </div>
        ) : (
          <div className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            {t('connectAndRun')}
          </div>
        )}
      </div>

      {/* Stock count funnel badge */}
      {resultCount !== undefined && resultCount !== null && (
        <div className="px-3 pb-2 flex items-center gap-1.5 animate-in fade-in duration-300">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200/60 dark:border-emerald-500/20 text-[10px] font-bold text-emerald-700 dark:text-emerald-400">
            <Eye className="h-3 w-3" />
            {t('stocksRemaining', { count: resultCount.toLocaleString() })}
          </span>
        </div>
      )}

      {/* Inline info popup (read-only) */}
      <NodeEditPopup selected={!!selected} onDelete={handleDelete}>
        <div className="text-[13px] text-gray-500 dark:text-gray-400 leading-relaxed">
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
