'use client';

import { useState, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Globe,
  Building2,
  Filter,
  GitMerge,
  Flag,
  ChevronDown,
  ChevronRight,
  GripVertical,
  Search,
  Loader2,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useConditions } from '@/contexts/ConditionsContext';
import type { StrategyConditionInfo } from '@/lib/api';

const IO_NODES = [
  { type: 'universe', shortKey: 'market', icon: Globe, color: 'text-emerald-600 dark:text-emerald-400', bgColor: 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20' },
  { type: 'sector', shortKey: 'sector', icon: Building2, color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20' },
  { type: 'output', shortKey: 'result', icon: Flag, color: 'text-orange-600 dark:text-orange-400', bgColor: 'bg-orange-50 dark:bg-orange-500/10 border-orange-200 dark:border-orange-500/20' },
];

const LOGIC_NODES = [
  { type: 'logic_and', shortKey: 'AND', hintKey: 'logicAndShort', icon: GitMerge, color: 'text-[#1313ec] dark:text-blue-400', bgColor: 'bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20', hoverBg: 'hover:bg-blue-100 dark:hover:bg-blue-500/20' },
  { type: 'logic_or', shortKey: 'OR', hintKey: 'logicOrShort', icon: GitMerge, color: 'text-purple-600 dark:text-purple-400', bgColor: 'bg-purple-50 dark:bg-purple-500/10 border-purple-200 dark:border-purple-500/20', hoverBg: 'hover:bg-purple-100 dark:hover:bg-purple-500/20' },
  { type: 'logic_not', shortKey: 'NOT', hintKey: 'logicNotShort', icon: GitMerge, color: 'text-red-600 dark:text-red-400', bgColor: 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/20', hoverBg: 'hover:bg-red-100 dark:hover:bg-red-500/20' },
];

function toTitleCaseFromKey(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function HelpTooltip({ targetRect, help }: { targetRect: DOMRect; help: string }) {
  const style: React.CSSProperties = {
    position: 'fixed',
    top: targetRect.top,
    left: targetRect.right + 8,
    zIndex: 9999,
  };

  return createPortal(
    <div style={style} className="w-56 p-2.5 rounded-lg bg-white dark:bg-[#1e1e1f] border border-[#e1e3e5] dark:border-[#2e2e30] shadow-lg pointer-events-none animate-in fade-in duration-100">
      <div className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
        {help}
      </div>
    </div>,
    document.body,
  );
}

function DraggableChip({
  type,
  label,
  icon: Icon,
  color,
  bgColor,
}: {
  type: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}) {
  const onDragStart = (event: React.DragEvent) => {
    event.dataTransfer.setData('application/reactflow-type', type);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-grab border ${bgColor} hover:shadow-sm transition-all text-xs font-medium`}
      draggable
      onDragStart={onDragStart}
    >
      <Icon className={`h-3.5 w-3.5 ${color} flex-shrink-0`} />
      <span className={`${color} truncate`}>{label}</span>
    </div>
  );
}

function LogicCard({
  type,
  label,
  hint,
  icon: Icon,
  color,
  bgColor,
  hoverBg,
}: {
  type: string;
  label: string;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  hoverBg: string;
}) {
  const onDragStart = (event: React.DragEvent) => {
    event.dataTransfer.setData('application/reactflow-type', type);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className={`flex flex-col items-center gap-0.5 px-1 py-2 rounded-lg cursor-grab border ${bgColor} ${hoverBg} hover:shadow-sm transition-all text-center flex-1 min-w-0`}
      draggable
      onDragStart={onDragStart}
    >
      <Icon className={`h-4 w-4 ${color}`} />
      <span className={`text-[11px] font-bold ${color} leading-tight`}>{label}</span>
      <span className="text-[9px] text-gray-400 dark:text-gray-500 leading-tight truncate w-full px-0.5">{hint}</span>
    </div>
  );
}

function DraggableItem({
  type,
  label,
  description,
  help,
  icon: Icon,
  color,
  conditionKey,
  recommendedLabel,
}: {
  type: string;
  label: string;
  description?: string;
  help?: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  conditionKey?: string;
  recommendedLabel?: string;
}) {
  const [hovered, setHovered] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  const onDragStart = (event: React.DragEvent) => {
    event.dataTransfer.setData('application/reactflow-type', type);
    if (conditionKey) {
      event.dataTransfer.setData('application/reactflow-condition', conditionKey);
    }
    event.dataTransfer.effectAllowed = 'move';
    setHovered(false);
  };

  const showTooltip = help
    ? () => {
        if (ref.current) setRect(ref.current.getBoundingClientRect());
        setHovered(true);
      }
    : undefined;

  return (
    <div
      ref={ref}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-grab border border-transparent hover:border-[#e1e3e5] dark:hover:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-all group"
      draggable
      onDragStart={onDragStart}
      onMouseEnter={showTooltip}
      onMouseLeave={() => setHovered(false)}
    >
      <GripVertical className="h-3 w-3 text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
      <Icon className={`h-4 w-4 ${color} flex-shrink-0`} />
      <div className="min-w-0">
        <div className="text-sm text-gray-700 dark:text-gray-200 font-medium truncate">
          {label}
          {recommendedLabel && (
            <span className="ml-1.5 inline-flex items-center px-1 py-0 text-[9px] font-bold rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 align-middle">
              {recommendedLabel}
            </span>
          )}
        </div>
        {description && (
          <div className="text-[11px] text-gray-400 dark:text-gray-500 truncate">
            {description}
          </div>
        )}
      </div>
      {hovered && help && rect && <HelpTooltip targetRect={rect} help={help} />}
    </div>
  );
}

interface NodePaletteProps {
  nodeCount?: number;
}

export default function NodePalette({ nodeCount }: NodePaletteProps) {
  const t = useTranslations('strategy');
  const tCond = useTranslations('conditions');
  const { categories, getConditionsByCategory, isLoading } = useConditions();
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const conditionsByCategory = useMemo(() => getConditionsByCategory(), [getConditionsByCategory]);
  const getCategoryLabel = (category: string): string => {
    const key = `categories.${category}`;
    return tCond.has(key) ? tCond(key) : toTitleCaseFromKey(category);
  };
  const getConditionLabel = (cond: StrategyConditionInfo): string => {
    const key = `${cond.key}.label`;
    return tCond.has(key) ? tCond(key) : (cond.label || toTitleCaseFromKey(cond.key));
  };
  const getConditionDesc = (cond: StrategyConditionInfo): string => {
    const key = `${cond.key}.desc`;
    return tCond.has(key) ? tCond(key) : (cond.description || '');
  };
  const getConditionHelp = (cond: StrategyConditionInfo): string | undefined => {
    const key = `${cond.key}.help`;
    if (tCond.has(key)) return tCond(key);
    return cond.description || undefined;
  };

  const toggleCategory = (cat: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  };

  const filteredConditions = useMemo(() => {
    if (!searchQuery.trim()) return conditionsByCategory;
    const q = searchQuery.toLowerCase();
    const result: Record<string, StrategyConditionInfo[]> = {};
    for (const [cat, conditions] of Object.entries(conditionsByCategory)) {
      const filtered = conditions.filter((c) => {
        const label = getConditionLabel(c).toLowerCase();
        const desc = getConditionDesc(c).toLowerCase();
        const key = c.key.toLowerCase();
        return label.includes(q) || desc.includes(q) || key.includes(q);
      });
      if (filtered.length > 0) result[cat] = filtered;
    }
    return result;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, conditionsByCategory]);

  const count = nodeCount ?? 0;
  const max = 20;
  const pct = Math.min((count / max) * 100, 100);

  return (
    <div className="w-64 h-full border-r border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] flex flex-col overflow-hidden">
      {/* Search */}
      <div className="px-3 pt-3 pb-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
          <input
            type="text"
            placeholder={t('searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-gray-50 dark:bg-[#1e1e1f] text-gray-700 dark:text-gray-200 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:border-[#1313ec] focus:ring-1 focus:ring-[#1313ec]/20 transition-colors"
          />
        </div>
      </div>

      {/* Input/Output nodes — compact row */}
      {!searchQuery.trim() && (
        <div className="px-3 pb-2 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
          <div className="px-0 py-1 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
            {t('inputNodes')}
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {IO_NODES.map((node) => (
              <DraggableChip
                key={node.type}
                type={node.type}
                label={t(node.shortKey)}
                icon={node.icon}
                color={node.color}
                bgColor={node.bgColor}
              />
            ))}
          </div>
        </div>
      )}

      {/* Scrollable filter conditions */}
      <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1">
        <div className="mb-2">
          {!searchQuery.trim() && (
            <div className="px-2 py-1.5 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
              {t('filterNodes')}
            </div>
          )}
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-xs">{t('loadingConditions')}</span>
            </div>
          ) : (
            categories.map((category) => {
              const conditions = filteredConditions[category] || [];
              if (conditions.length === 0) return null;
              const isExpanded = !collapsedCategories.has(category) || !!searchQuery.trim();

              return (
                <div key={category} className="mb-1">
                  <button
                    type="button"
                    onClick={() => toggleCategory(category)}
                    className="flex items-center gap-1.5 px-2 py-1.5 w-full text-left text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors rounded"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    <span>{getCategoryLabel(category)}</span>
                    <span className="ml-auto text-[10px] font-normal text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 rounded-full">
                      {conditions.length}
                    </span>
                  </button>
                  {isExpanded &&
                    conditions.map((cond) => (
                      <DraggableItem
                        key={cond.key}
                        type="condition"
                        label={getConditionLabel(cond)}
                        description={getConditionDesc(cond)}
                        help={getConditionHelp(cond)}
                        icon={Filter}
                        color="text-[#1313ec] dark:text-blue-400"
                        conditionKey={cond.key}
                        recommendedLabel={cond.recommended ? tCond('recommended') : undefined}
                      />
                    ))}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Pinned Logic Operators — always visible */}
      <div className="px-3 py-2 border-t border-[#e1e3e5] dark:border-[#2e2e30]">
        <div className="px-0 py-1 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
          {t('logicOperators')}
        </div>
        <div className="flex gap-1.5">
          {LOGIC_NODES.map((node) => (
            <LogicCard
              key={node.type}
              type={node.type}
              label={node.shortKey}
              hint={t(node.hintKey)}
              icon={node.icon}
              color={node.color}
              bgColor={node.bgColor}
              hoverBg={node.hoverBg}
            />
          ))}
        </div>
      </div>

      {/* Footer with progress bar */}
      <div className="px-3 py-2 border-t border-[#e1e3e5] dark:border-[#2e2e30]">
        <div className="flex items-center justify-between text-[11px] text-gray-400 dark:text-gray-500 mb-1">
          <span>{t('nodeLimit', { count, max })}</span>
          <span className={count >= max ? 'text-red-500 font-semibold' : ''}>{count}/{max}</span>
        </div>
        <div className="h-1 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${count >= max ? 'bg-red-500' : count >= max * 0.8 ? 'bg-amber-500' : 'bg-[#1313ec]'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
