'use client';

import { memo, useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Plus, Check, Pencil } from 'lucide-react';
import { useTranslations } from 'next-intl';
import MarkdownMessage from './MarkdownMessage';

interface StructuredSuggestion {
  condition_type: string;
  params: Record<string, unknown>;
  rationale: string;
}

interface StructuredPayload {
  summary?: string;
  suggestions?: StructuredSuggestion[];
  warnings?: string[];
}

interface NodeMapping {
  condition_type: string;
  node_type: string;
  params: Record<string, unknown>;
  label: string;
}

interface ExistingConditionNode {
  id: string;
  condition_type: string;
}

interface SectionedMessageProps {
  content: string;
  payload: StructuredPayload;
  nodeMappings?: NodeMapping[];
  onAddNodes?: (nodes: NodeMapping[]) => void;
  existingConditionNodes?: ExistingConditionNode[];
  onUpdateNode?: (nodeId: string, params: Record<string, unknown>) => void;
}

function SectionedMessage({
  content,
  payload,
  nodeMappings,
  onAddNodes,
  existingConditionNodes,
  onUpdateNode,
}: SectionedMessageProps) {
  const t = useTranslations('strategy');
  const tCond = useTranslations('conditions');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    suggestions: true,
    warnings: true,
  });
  // Track per-suggestion action state with the action type taken
  const [actionStates, setActionStates] = useState<Record<number, 'added' | 'updated'>>({});

  // Map condition_type → existing node id for quick lookup
  const existingMap = useMemo(() => {
    const map = new Map<string, string>();
    if (existingConditionNodes) {
      for (const node of existingConditionNodes) {
        // First match wins (if multiple nodes have same condition_type)
        if (!map.has(node.condition_type)) {
          map.set(node.condition_type, node.id);
        }
      }
    }
    return map;
  }, [existingConditionNodes]);

  const getConditionLabel = (key: string): string => {
    const labelKey = `${key}.label`;
    if (tCond.has(labelKey)) return tCond(labelKey);
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const getParamLabel = (condKey: string, paramKey: string): string => {
    const pKey = `${condKey}.params.${paramKey}`;
    if (tCond.has(pKey)) return tCond(pKey);
    return paramKey;
  };

  const toggle = (key: string) =>
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));

  const handleAddSingle = (index: number, mapping: NodeMapping) => {
    if (!onAddNodes) return;
    onAddNodes([mapping]);
    setActionStates(prev => ({ ...prev, [index]: 'added' }));
  };

  const handleUpdateSingle = (index: number, conditionType: string, params: Record<string, unknown>) => {
    const nodeId = existingMap.get(conditionType);
    if (!nodeId || !onUpdateNode) return;
    onUpdateNode(nodeId, params);
    setActionStates(prev => ({ ...prev, [index]: 'updated' }));
  };

  return (
    <div className="space-y-2">
      {/* Main text content */}
      <MarkdownMessage content={content} />

      {/* Summary card */}
      {payload.summary && (
        <div className="rounded-lg border border-blue-200/60 bg-blue-50/50 px-3 py-2 text-xs text-blue-800 dark:border-blue-500/20 dark:bg-blue-900/10 dark:text-blue-200">
          <span className="font-semibold">{t('chatbot.summary')}: </span>
          {payload.summary}
        </div>
      )}

      {/* Suggestions section */}
      {payload.suggestions && payload.suggestions.length > 0 && (
        <div className="rounded-lg border border-gray-200/80 dark:border-gray-700/60">
          <div className="flex items-center px-3 py-1.5">
            <button
              type="button"
              onClick={() => toggle('suggestions')}
              className="flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300"
            >
              {expandedSections.suggestions ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              {t('chatbot.conditions', { count: payload.suggestions.length })}
            </button>
          </div>
          {expandedSections.suggestions && (
            <div className="space-y-1 px-3 pb-2">
              {payload.suggestions.map((s, j) => {
                const candidate = nodeMappings?.[j];
                const mapping = candidate?.condition_type === s.condition_type
                  ? candidate
                  : nodeMappings?.find(m => m.condition_type === s.condition_type);
                const existingNodeId = existingMap.get(s.condition_type);
                const actionTaken = actionStates[j];

                return (
                  <div
                    key={j}
                    className="rounded-lg border border-blue-200/60 bg-blue-50 px-2.5 py-1.5 dark:border-blue-500/20 dark:bg-blue-900/20"
                  >
                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="font-semibold text-blue-700 dark:text-blue-300">
                        {getConditionLabel(s.condition_type)}
                      </span>
                      {s.params &&
                        typeof s.params === 'object' &&
                        !Array.isArray(s.params) &&
                        Object.entries(s.params).map(([k, v]) => (
                          <span
                            key={k}
                            className="rounded bg-blue-100 px-1 py-0.5 text-[10px] text-blue-600 dark:bg-blue-800/30 dark:text-blue-400"
                          >
                            {getParamLabel(s.condition_type, k)}={String(v)}
                          </span>
                        ))}
                    </div>
                    {s.rationale && (
                      <p className="mt-1 text-[11px] leading-snug text-gray-600 dark:text-gray-400">
                        {s.rationale}
                      </p>
                    )}
                    {/* Per-suggestion action button */}
                    <div className="mt-1.5 flex justify-end">
                      {actionTaken ? (
                        <span className="flex items-center gap-1 text-[10px] font-medium text-green-600 dark:text-green-400">
                          <Check className="h-3 w-3" />
                          {actionTaken === 'updated'
                            ? t('chatbot.updated')
                            : t('chatbot.added')}
                        </span>
                      ) : existingNodeId && onUpdateNode ? (
                        <button
                          type="button"
                          onClick={() => handleUpdateSingle(j, s.condition_type, s.params)}
                          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-amber-600 transition-colors hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-900/20"
                        >
                          <Pencil className="h-3 w-3" />
                          {t('chatbot.updateExisting')}
                        </button>
                      ) : mapping && onAddNodes ? (
                        <button
                          type="button"
                          onClick={() => handleAddSingle(j, mapping)}
                          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-blue-600 transition-colors hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
                        >
                          <Plus className="h-3 w-3" />
                          {t('chatbot.addNew')}
                        </button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Warnings section */}
      {payload.warnings && payload.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200/60 dark:border-amber-500/20">
          <button
            type="button"
            onClick={() => toggle('warnings')}
            className="flex w-full items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-amber-700 dark:text-amber-300"
          >
            {expandedSections.warnings ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            {t('chatbot.warnings', { count: payload.warnings.length })}
          </button>
          {expandedSections.warnings && (
            <div className="space-y-1 px-3 pb-2">
              {payload.warnings.map((w, j) => (
                <div
                  key={j}
                  className="rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
                >
                  {w}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(SectionedMessage);
