'use client';

import { memo, useMemo } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { GitMerge } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';

const OPERATOR_STYLES: Record<
  string,
  { bg: string; border: string; badge: string; text: string }
> = {
  and: {
    bg: 'bg-blue-50/50 dark:bg-blue-500/5',
    border: 'border-blue-300/40 dark:border-blue-500/20',
    badge: 'bg-[#1313ec] text-white',
    text: 'text-[#1313ec] dark:text-blue-400',
  },
  or: {
    bg: 'bg-purple-50/50 dark:bg-purple-500/5',
    border: 'border-purple-300/40 dark:border-purple-500/20',
    badge: 'bg-purple-600 text-white',
    text: 'text-purple-600 dark:text-purple-400',
  },
  not: {
    bg: 'bg-red-50/50 dark:bg-red-500/5',
    border: 'border-red-300/40 dark:border-red-500/20',
    badge: 'bg-red-600 text-white',
    text: 'text-red-600 dark:text-red-400',
  },
};

const OPERATOR_LABELS: Record<string, string> = {
  and: 'andGroup',
  or: 'orGroup',
  not: 'notGroup',
};

function GroupNode({ id, data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const nodeData = data as unknown as StrategyNodeData;
  const op = (nodeData.logic_operator || 'and').toLowerCase();
  const style = OPERATOR_STYLES[op] || OPERATOR_STYLES.and;
  const labelKey = OPERATOR_LABELS[op] || 'andGroup';

  const { getNodes } = useReactFlow();

  const childCount = useMemo(() => {
    return getNodes().filter((n) => n.parentId === id).length;
  }, [getNodes, id]);

  return (
    <div
      className={`relative rounded-2xl border-2 border-dashed ${style.border} ${style.bg} transition-shadow ${
        selected
          ? 'shadow-[0_0_0_2px_rgba(19,19,236,0.3)] ring-2 ring-[#1313ec]/10'
          : 'shadow-sm hover:shadow-md'
      }`}
      style={{ width: '100%', height: '100%', minWidth: 280, minHeight: 200 }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[7px] hover:!scale-125 !transition-transform"
      />

      {/* Badge */}
      <div className="absolute -top-3 left-4 z-10">
        <span
          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${style.badge}`}
        >
          <GitMerge className="h-3 w-3" />
          {t(labelKey)}
        </span>
      </div>

      {/* Drop zone hint */}
      {childCount === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className={`text-xs ${style.text} opacity-60`}>
            {t('emptyGroup')}
          </p>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[7px] hover:!scale-125 !transition-transform"
      />
    </div>
  );
}

export default memo(GroupNode);
