'use client';

import { memo, useCallback } from 'react';
import { Handle, Position, useNodeId, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Globe } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import NodeEditPopup, { FieldLabel } from './NodeEditPopup';

const UNIVERSES = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ100'] as const;

function parseUniverses(value?: string): string[] {
  if (!value) return ['KOSPI'];
  const parsed = value
    .split(',')
    .map((item) => item.trim())
    .filter((item): item is (typeof UNIVERSES)[number] =>
      (UNIVERSES as readonly string[]).includes(item)
    );
  return parsed.length > 0 ? parsed : ['KOSPI'];
}

function toUniverseValue(values: string[]): string {
  return values.join(',');
}

function UniverseNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const nodeData = data as unknown as StrategyNodeData;
  const nodeId = useNodeId()!;
  const { updateNodeData, deleteElements } = useReactFlow();
  const selectedUniverses = parseUniverses(nodeData.universe);

  const handleUniverseToggle = useCallback(
    (value: string) => {
      const current = parseUniverses(nodeData.universe);
      const exists = current.includes(value);

      let next: string[];
      if (exists) {
        if (current.length === 1) return;
        next = current.filter((item) => item !== value);
      } else {
        next = [...current, value];
      }

      updateNodeData(nodeId, { universe: toUniverseValue(next) });
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
        <div className="text-[13px] font-bold text-gray-900 dark:text-gray-100">
          {t('marketSelection')}
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          {t('composite', { universe: selectedUniverses.join(' + ') })}
        </div>
      </div>
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
            {UNIVERSES.map((universe) => (
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
              </label>
            ))}
          </div>
        </div>
      </NodeEditPopup>
    </div>
  );
}

export default memo(UniverseNode);
