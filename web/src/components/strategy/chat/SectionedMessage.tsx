'use client';

import { memo, useState } from 'react';
import { ChevronDown, ChevronRight, Plus, Check } from 'lucide-react';
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

interface SectionedMessageProps {
  content: string;
  payload: StructuredPayload;
  nodeMappings?: NodeMapping[];
  onAddNodes?: (nodes: NodeMapping[]) => void;
}

function SectionedMessage({ content, payload, nodeMappings, onAddNodes }: SectionedMessageProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    suggestions: true,
    warnings: true,
  });
  const [added, setAdded] = useState(false);

  const toggle = (key: string) =>
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));

  const handleAddAll = () => {
    if (!nodeMappings?.length || !onAddNodes) return;
    onAddNodes(nodeMappings);
    setAdded(true);
  };

  return (
    <div className="space-y-2">
      {/* Main text content */}
      <MarkdownMessage content={content} />

      {/* Summary card */}
      {payload.summary && (
        <div className="rounded-lg border border-blue-200/60 bg-blue-50/50 px-3 py-2 text-xs text-blue-800 dark:border-blue-500/20 dark:bg-blue-900/10 dark:text-blue-200">
          <span className="font-semibold">Summary: </span>
          {payload.summary}
        </div>
      )}

      {/* Suggestions section */}
      {payload.suggestions && payload.suggestions.length > 0 && (
        <div className="rounded-lg border border-gray-200/80 dark:border-gray-700/60">
          <div className="flex items-center justify-between px-3 py-1.5">
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
              Conditions ({payload.suggestions.length})
            </button>
            {/* Add to Canvas button */}
            {nodeMappings && nodeMappings.length > 0 && onAddNodes && (
              <button
                type="button"
                onClick={handleAddAll}
                disabled={added}
                className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-blue-600 transition-colors hover:bg-blue-50 disabled:text-green-600 disabled:hover:bg-transparent dark:text-blue-400 dark:hover:bg-blue-900/20 dark:disabled:text-green-400"
              >
                {added ? (
                  <>
                    <Check className="h-3 w-3" />
                    Added
                  </>
                ) : (
                  <>
                    <Plus className="h-3 w-3" />
                    Add to Canvas
                  </>
                )}
              </button>
            )}
          </div>
          {expandedSections.suggestions && (
            <div className="space-y-1 px-3 pb-2">
              {payload.suggestions.map((s, j) => (
                <div
                  key={j}
                  className="rounded-lg border border-blue-200/60 bg-blue-50 px-2.5 py-1.5 dark:border-blue-500/20 dark:bg-blue-900/20"
                >
                  <div className="flex flex-wrap items-center gap-1.5 text-xs">
                    <span className="font-mono font-semibold text-blue-700 dark:text-blue-300">
                      {s.condition_type}
                    </span>
                    {s.params &&
                      typeof s.params === 'object' &&
                      !Array.isArray(s.params) &&
                      Object.entries(s.params).map(([k, v]) => (
                        <span
                          key={k}
                          className="rounded bg-blue-100 px-1 py-0.5 text-[10px] text-blue-600 dark:bg-blue-800/30 dark:text-blue-400"
                        >
                          {k}={String(v)}
                        </span>
                      ))}
                  </div>
                  {s.rationale && (
                    <p className="mt-1 text-[11px] leading-snug text-gray-600 dark:text-gray-400">
                      {s.rationale}
                    </p>
                  )}
                </div>
              ))}
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
            Warnings ({payload.warnings.length})
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
