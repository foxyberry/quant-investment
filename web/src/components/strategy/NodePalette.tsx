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

const SPECIAL_NODES = [
  { type: 'universe', labelKey: 'marketSelection', icon: Globe, color: 'text-emerald-600 dark:text-emerald-400' },
  { type: 'sector', labelKey: 'sectorFilter', icon: Building2, color: 'text-amber-600 dark:text-amber-400' },
  { type: 'logic_and', labelKey: 'andGroup', icon: GitMerge, color: 'text-[#1313ec] dark:text-blue-400' },
  { type: 'logic_or', labelKey: 'orGroup', icon: GitMerge, color: 'text-purple-600 dark:text-purple-400' },
  { type: 'logic_not', labelKey: 'notGroup', icon: GitMerge, color: 'text-red-600 dark:text-red-400' },
  { type: 'output', labelKey: 'finalOutput', icon: Flag, color: 'text-orange-600 dark:text-orange-400' },
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
  // Track collapsed categories (all expanded by default)
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
      const filtered = conditions.filter(
        (c) =>
          c.label.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q)
      );
      if (filtered.length > 0) result[cat] = filtered;
    }
    return result;
  }, [searchQuery, conditionsByCategory]);

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

      <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1">
        {/* Input Nodes */}
        {!searchQuery && (
          <div className="mb-2">
            <div className="px-2 py-1.5 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
              {t('inputNodes')}
            </div>
            {SPECIAL_NODES.filter((n) => n.type === 'universe' || n.type === 'sector').map((node) => (
              <DraggableItem
                key={node.type}
                type={node.type}
                label={t(node.labelKey)}
                icon={node.icon}
                color={node.color}
              />
            ))}
          </div>
        )}

        {/* Filter Nodes (conditions) */}
        <div className="mb-2">
          {!searchQuery && (
            <div className="px-2 py-1.5 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
              {t('filterNodes')}
            </div>
          )}
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-xs">Loading conditions...</span>
            </div>
          ) : (
            categories.map((category) => {
              const conditions = filteredConditions[category] || [];
              if (conditions.length === 0) return null;
              const isExpanded = !collapsedCategories.has(category) || !!searchQuery;

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

        {/* Logic Operators */}
        {!searchQuery && (
          <div>
            <div className="px-2 py-1.5 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
              {t('logicOperators')}
            </div>
            <div className="space-y-1 px-1 pt-1">
              {SPECIAL_NODES.filter((n) => n.type.startsWith('logic_')).map((node) => (
                <DraggableItem
                  key={node.type}
                  type={node.type}
                  label={t(node.labelKey)}
                  description={t('dropConditionHere')}
                  icon={node.icon}
                  color={node.color}
                />
              ))}
            </div>
            {/* Output node */}
            <div className="mt-2">
              {SPECIAL_NODES.filter((n) => n.type === 'output').map((node) => (
                <DraggableItem
                  key={node.type}
                  type={node.type}
                  label={t(node.labelKey)}
                  icon={node.icon}
                  color={node.color}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="px-3 py-2 border-t border-[#e1e3e5] dark:border-[#2e2e30] text-[11px] text-gray-400 dark:text-gray-500">
        {t('nodeLimit', { count: nodeCount ?? 0, max: 20 })}
      </div>
    </div>
  );
}
