'use client';

import { memo, useCallback } from 'react';
import { Handle, Position, useNodeId, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Globe, Eye } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import {
  SUPPORTED_UNIVERSES,
  parseUniverseSelection,
  serializeUniverseSelection,
  type SupportedUniverse,
  type StrategyNodeData,
} from '@/lib/strategy/graphSerializer';
import { useUniverses } from '@/hooks/useScreening';
import NodeEditPopup, { FieldLabel } from './NodeEditPopup';

function UniverseNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const locale = useLocale();
  const nodeData = data as unknown as StrategyNodeData;
  const nodeId = useNodeId()!;
  const { updateNodeData, deleteElements } = useReactFlow();
  const selectedUniverses = parseUniverseSelection(nodeData.universe);
  const universesQuery = useUniverses();

  const stockCountMap: Record<string, number> = {};
  for (const universe of universesQuery.data ?? []) {
    stockCountMap[universe.name] = universe.stock_count;
  }
  const selectedCountText = selectedUniverses.map((u) => {
    const count = stockCountMap[u];
    return count !== undefined
      ? `${u} (${count.toLocaleString(locale)})`
      : u;
  });
  const totalSelectedCount = selectedUniverses.reduce(
    (sum, u) => sum + (stockCountMap[u] ?? 0),
    0
  );

  const handleUniverseToggle = useCallback(
    (value: SupportedUniverse) => {
      const current = parseUniverseSelection(nodeData.universe);
      const exists = current.includes(value);

      let next: SupportedUniverse[];
      if (exists) {
        if (current.length === 1) return;
        next = current.filter((item) => item !== value);
      } else {
        next = [...current, value];
      }

      updateNodeData(nodeId, { universe: serializeUniverseSelection(next) });
    },
    [nodeData.universe, nodeId, updateNodeData]
  );

  const handleDelete = useCallback(() => {
    deleteElements({ nodes: [{ id: nodeId }] });
  }, [nodeId, deleteElements]);

  return (
    <div
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border min-w-[200px] transition-shadow ${
        selected
          ? 'border-2 border-[#1313ec] shadow-xl'
          : 'border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:shadow-md'
      }`}
    >
      {/* Header bar */}
      <div className="px-3 py-2 border-b border-[#e1e3e5] dark:border-[#2e2e30] bg-slate-50 dark:bg-slate-800/50 rounded-t-[7px] flex items-center gap-2">
        <Globe className="h-3.5 w-3.5 text-[#1313ec] dark:text-blue-400" />
        <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          {t('inputBadge')}
        </span>
      </div>
      {/* Content */}
      <div className="p-3">
        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {t('marketSelection')}
        </div>
        <div className="text-[13px] text-slate-500 dark:text-slate-400 mt-1">
          {t('composite', { universe: selectedCountText.join(' + ') })}
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          {t('selectedUniverseTotal', {
            count: totalSelectedCount.toLocaleString(locale),
          })}
        </div>
      </div>

      {/* Stock count funnel badge */}
      {nodeData.intermediateResult && nodeData.intermediateResult.stock_count != null && (
        <div className="px-3 pb-2 flex items-center gap-1.5 animate-in fade-in duration-300">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200/60 dark:border-emerald-500/20 text-[10px] font-bold text-emerald-700 dark:text-emerald-400">
            <Eye className="h-3 w-3" />
            {t('stocksRemaining', { count: nodeData.intermediateResult.stock_count.toLocaleString() })}
          </span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[7px] hover:!scale-125 !transition-transform"
      />

      {/* Inline edit popup */}
      <NodeEditPopup selected={!!selected} onDelete={handleDelete}>
        <div>
          <FieldLabel>{t('stockUniverse')}</FieldLabel>
          <div className="space-y-2">
            {SUPPORTED_UNIVERSES.map((universe) => (
              <label
                key={universe}
                className="flex items-center gap-2.5 rounded-md border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2 text-sm text-gray-700 dark:text-gray-200"
              >
                <input
                  type="checkbox"
                  checked={selectedUniverses.includes(universe)}
                  onChange={() => handleUniverseToggle(universe)}
                  className="rounded border-[#d0d4d9] text-[#1313ec] focus:ring-[#1313ec]/20"
                />
                <span>{universe}</span>
                {stockCountMap[universe] !== undefined && (
                  <span className="ml-auto text-xs text-gray-500 dark:text-gray-400">
                    {stockCountMap[universe].toLocaleString(locale)} {t('stockCount')}
                  </span>
                )}
              </label>
            ))}
          </div>
        </div>
      </NodeEditPopup>
    </div>
  );
}

export default memo(UniverseNode);
