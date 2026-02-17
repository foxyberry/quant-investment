'use client';

import { memo, useMemo } from 'react';
import { Handle, NodeResizer, Position, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { GitMerge } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';

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
  const resizerColor = OPERATOR_RESIZER_COLORS[op] || OPERATOR_RESIZER_COLORS.and;

  const { getNodes } = useReactFlow();

  const childCount = useMemo(() => {
    return getNodes().filter((n) => n.parentId === id).length;
  }, [getNodes, id]);

  return (
    <div
      className={`relative rounded-2xl border ${style.border} ${style.bg} transition-shadow ${
        selected
          ? 'shadow-[0_0_0_2px_rgba(19,19,236,0.3)] ring-2 ring-[#1313ec]/10'
          : 'shadow-sm hover:shadow-md'
      }`}
      style={{ width: '100%', height: '100%', minWidth: 280, minHeight: 200 }}
      onDragOver={(e) => e.preventDefault()}
    >
      <NodeResizer
        isVisible={selected}
        minWidth={280}
        minHeight={200}
        color={resizerColor}
        lineStyle={{ borderColor: resizerColor }}
      />

      <Handle
        type="target"
        position={Position.Left}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[7px] hover:!scale-125 !transition-transform"
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
        <p className="text-[11px] text-white/60 mt-0.5">
          {t('multiFilterGroup')}
        </p>
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
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[7px] hover:!scale-125 !transition-transform"
      />
    </div>
  );
}

export default memo(GroupNode);
