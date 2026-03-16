'use client';

import { memo, useMemo, useCallback } from 'react';
import { Handle, NodeResizer, Position, useReactFlow, useNodeId } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { GitMerge } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import NodeEditPopup, { FieldLabel, MatchedCountBadge, SelectInput } from './NodeEditPopup';

const OPERATOR_STYLES: Record<
  string,
  { bg: string; border: string; headerBg: string; headerBorder: string; badge: string; text: string }
> = {
  and: {
    bg: 'bg-blue-50/30 dark:bg-blue-500/5',
    border: 'border-blue-200/60 dark:border-blue-500/20',
    headerBg: 'bg-[#1313ec]',
    headerBorder: 'border-blue-600',
    badge: 'bg-white/20 text-white',
    text: 'text-[#1313ec] dark:text-blue-400',
  },
  or: {
    bg: 'bg-purple-50/30 dark:bg-purple-500/5',
    border: 'border-purple-200/60 dark:border-purple-500/20',
    headerBg: 'bg-purple-600',
    headerBorder: 'border-purple-700',
    badge: 'bg-white/20 text-white',
    text: 'text-purple-600 dark:text-purple-400',
  },
  not: {
    bg: 'bg-red-50/30 dark:bg-red-500/5',
    border: 'border-red-200/60 dark:border-red-500/20',
    headerBg: 'bg-red-600',
    headerBorder: 'border-red-700',
    badge: 'bg-white/20 text-white',
    text: 'text-red-600 dark:text-red-400',
  },
};

const OPERATOR_TITLES: Record<string, string> = {
  and: 'andGroupTitle',
  or: 'orGroupTitle',
  not: 'notGroupTitle',
};

const OPERATOR_LABELS: Record<string, string> = {
  and: 'andGroup',
  or: 'orGroup',
  not: 'notGroup',
};

const OPERATOR_SUBTITLES: Record<string, string> = {
  and: 'allConditionsMustMatch',
  or: 'anyConditionMustMatch',
  not: 'invertFirstCondition',
};

const OPERATOR_CONNECTOR: Record<string, string> = {
  and: '&',
  or: '|',
  not: '!',
};

const CONNECTOR_STYLES: Record<string, string> = {
  and: 'bg-blue-100 dark:bg-blue-500/20 border-blue-300 dark:border-blue-500/40 text-[#1313ec] dark:text-blue-400',
  or: 'bg-purple-100 dark:bg-purple-500/20 border-purple-300 dark:border-purple-500/40 text-purple-600 dark:text-purple-400',
  not: 'bg-red-100 dark:bg-red-500/20 border-red-300 dark:border-red-500/40 text-red-600 dark:text-red-400',
};

const OPERATOR_RESIZER_COLORS: Record<string, string> = {
  and: '#1313ec',
  or: '#9333ea',
  not: '#dc2626',
};

function GroupNode({ id, data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const nodeData = data as unknown as StrategyNodeData;
  const op = (nodeData.logic_operator || 'and').toLowerCase();
  const style = OPERATOR_STYLES[op] || OPERATOR_STYLES.and;
  const titleKey = OPERATOR_TITLES[op] || 'andGroupTitle';
  const labelKey = OPERATOR_LABELS[op] || 'andGroup';
  const subtitleKey = OPERATOR_SUBTITLES[op] || 'allConditionsMustMatch';
  const connectorSymbol = OPERATOR_CONNECTOR[op] || '&';
  const connectorStyle = CONNECTOR_STYLES[op] || CONNECTOR_STYLES.and;
  const resizerColor = OPERATOR_RESIZER_COLORS[op] || OPERATOR_RESIZER_COLORS.and;
  const intermediateResult = nodeData.intermediateResult;

  const nodeId = useNodeId()!;
  const { getNodes, updateNodeData, deleteElements } = useReactFlow();

  const childCount = useMemo(() => {
    return getNodes().filter((n) => n.parentId === id).length;
  }, [getNodes, id]);

  const dynamicMinHeight = useMemo(() => {
    if (childCount <= 1) return 220;
    return 220 + (childCount - 1) * 120;
  }, [childCount]);

  const handleOperatorChange = useCallback(
    (value: string) => {
      updateNodeData(nodeId, { logic_operator: value });
    },
    [nodeId, updateNodeData]
  );

  const handleDelete = useCallback(() => {
    // Delete group and all children
    const children = getNodes().filter((n) => n.parentId === id);
    const nodesToDelete = [{ id: nodeId }, ...children.map((c) => ({ id: c.id }))];
    deleteElements({ nodes: nodesToDelete });
  }, [nodeId, id, getNodes, deleteElements]);

  return (
    <div
      className={`relative rounded-2xl border ${style.border} ${style.bg} transition-shadow ${
        selected
          ? 'shadow-xl ring-2 ring-[#1313ec]/20'
          : 'shadow-sm hover:shadow-md'
      }`}
      style={{ width: '100%', height: '100%', minWidth: 380, minHeight: dynamicMinHeight }}
      onDragOver={(e) => e.preventDefault()}
    >
      <NodeResizer
        isVisible={selected}
        minWidth={380}
        minHeight={dynamicMinHeight}
        color={resizerColor}
        lineStyle={{ borderColor: resizerColor }}
      />

      <Handle
        type="target"
        position={Position.Left}
        className="!w-5 !h-5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[10px] hover:!scale-125 !transition-transform"
      />

      {/* Header */}
      <div className={`px-4 py-2.5 rounded-t-[14px] ${style.headerBg}`}>
        <div className="flex items-center gap-2">
          <GitMerge className="h-4 w-4 text-white/80" />
          <span className="text-[11px] font-bold text-white uppercase tracking-wider">
            {t(titleKey)}
          </span>
          <span className={`ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${style.badge}`}>
            {t(labelKey)}
          </span>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <p className="text-[11px] text-white/60">
            {t(subtitleKey)}
          </p>
          {intermediateResult && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-white/15 text-[10px] font-bold text-white">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
              {intermediateResult.stock_count.toLocaleString()} {t('stockCount')}
            </span>
          )}
        </div>
      </div>

      {/* Children area */}
      <div className="relative" style={{ minHeight: 120 }}>
        {childCount === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className={`text-xs ${style.text} opacity-50`}>
              {t('emptyGroup')}
            </p>
          </div>
        )}
        {childCount > 1 && (
          <div className="absolute left-1/2 top-[60px] bottom-[28px] -translate-x-1/2 flex flex-col items-center justify-evenly pointer-events-none">
            {Array.from({ length: childCount - 1 }).map((_, i) => (
              <div
                key={i}
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 ${connectorStyle}`}
              >
                {connectorSymbol}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stock count badge below children area */}
      {intermediateResult && (
        <div className="px-4 pb-2">
          <MatchedCountBadge count={intermediateResult.stock_count} />
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-5 !h-5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[10px] hover:!scale-125 !transition-transform"
      />

      {/* Inline edit popup */}
      <NodeEditPopup selected={!!selected} onDelete={handleDelete}>
        <div>
          <FieldLabel>{t('logicOperator')}</FieldLabel>
          <SelectInput
            value={nodeData.logic_operator || 'and'}
            onChange={handleOperatorChange}
          >
            <option value="and">{t('andAllMustMatch')}</option>
            <option value="or">{t('orAnyMustMatch')}</option>
            <option value="not">{t('notInvertFirst')}</option>
          </SelectInput>
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
          {t('groupInstruction')}
        </div>
      </NodeEditPopup>
    </div>
  );
}

export default memo(GroupNode);
