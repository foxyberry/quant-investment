'use client';

import { useState, useMemo } from 'react';
import {
  Globe,
  Filter,
  GitMerge,
  Flag,
  ChevronDown,
  ChevronRight,
  GripVertical,
  Search,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import {
  CATEGORIES,
  getConditionsByCategory,
} from '@/lib/strategy/conditionRegistry';
import type { ConditionMeta } from '@/lib/strategy/conditionRegistry';

const SPECIAL_NODES = [
  { type: 'universe', labelKey: 'marketSelection', icon: Globe, color: 'text-emerald-600 dark:text-emerald-400' },
  { type: 'logic_and', labelKey: 'andGate', icon: GitMerge, color: 'text-[#1313ec] dark:text-blue-400' },
  { type: 'logic_or', labelKey: 'orGate', icon: GitMerge, color: 'text-purple-600 dark:text-purple-400' },
  { type: 'logic_not', labelKey: 'notGate', icon: GitMerge, color: 'text-red-600 dark:text-red-400' },
  { type: 'output', labelKey: 'finalOutput', icon: Flag, color: 'text-orange-600 dark:text-orange-400' },
];

function DraggableItem({
  type,
  label,
  description,
  icon: Icon,
  color,
  conditionKey,
}: {
  type: string;
  label: string;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  conditionKey?: string;
}) {
  const onDragStart = (event: React.DragEvent) => {
    event.dataTransfer.setData('application/reactflow-type', type);
    if (conditionKey) {
      event.dataTransfer.setData('application/reactflow-condition', conditionKey);
    }
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-grab border border-transparent hover:border-[#e1e3e5] dark:hover:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-all group"
      draggable
      onDragStart={onDragStart}
    >
      <GripVertical className="h-3 w-3 text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
      <Icon className={`h-4 w-4 ${color} flex-shrink-0`} />
      <div className="min-w-0">
        <div className="text-sm text-gray-700 dark:text-gray-200 font-medium truncate">{label}</div>
        {description && (
          <div className="text-[11px] text-gray-400 dark:text-gray-500 truncate">
            {description}
          </div>
        )}
      </div>
    </div>
  );
}

export default function NodePalette() {
  const t = useTranslations('strategy');
  const tCond = useTranslations('conditions');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(CATEGORIES)
  );
  const [searchQuery, setSearchQuery] = useState('');
  const conditionsByCategory = getConditionsByCategory();

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => {
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
    const result: Record<string, ConditionMeta[]> = {};
    for (const [cat, conditions] of Object.entries(conditionsByCategory)) {
      const filtered = conditions.filter(
        (c: ConditionMeta) =>
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
            {SPECIAL_NODES.filter((n) => n.type === 'universe').map((node) => (
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
          {CATEGORIES.map((category) => {
            const conditions = filteredConditions[category] || [];
            if (conditions.length === 0) return null;
            const isExpanded = expandedCategories.has(category) || !!searchQuery;

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
                  <span>{tCond('categories.' + category)}</span>
                  <span className="ml-auto text-[10px] font-normal text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 rounded-full">
                    {conditions.length}
                  </span>
                </button>
                {isExpanded &&
                  conditions.map((cond: ConditionMeta) => (
                    <DraggableItem
                      key={cond.key}
                      type="condition"
                      label={tCond(cond.key + '.label')}
                      description={tCond(cond.key + '.desc')}
                      icon={Filter}
                      color="text-[#1313ec] dark:text-blue-400"
                      conditionKey={cond.key}
                    />
                  ))}
              </div>
            );
          })}
        </div>

        {/* Logic Operators */}
        {!searchQuery && (
          <div>
            <div className="px-2 py-1.5 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
              {t('logicOperators')}
            </div>
            <div className="flex gap-2 px-2 pt-1">
              {SPECIAL_NODES.filter((n) => n.type.startsWith('logic_')).map((node) => {
                const label = node.type.replace('logic_', '').toUpperCase();
                return (
                  <div
                    key={node.type}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg cursor-grab border border-[#e1e3e5] dark:border-[#2e2e30] bg-gray-50 dark:bg-[#1e1e1f] hover:border-[#1313ec] transition-colors text-xs font-bold text-gray-600 dark:text-gray-300"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('application/reactflow-type', node.type);
                      e.dataTransfer.effectAllowed = 'move';
                    }}
                  >
                    {label}
                  </div>
                );
              })}
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
    </div>
  );
}
