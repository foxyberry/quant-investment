'use client';

import { memo, useCallback, useState } from 'react';
import { Handle, Position, useNodeId, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Filter, CheckCircle2, CircleDashed, Info, Eye, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { getDownstreamNodeIds, type StrategyNodeData } from '@/lib/strategy/graphSerializer';
import type { ConditionParam } from '@/lib/strategy/conditionRegistry';
import { useConditions } from '@/contexts/ConditionsContext';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import NodeEditPopup, {
  FieldLabel,
  SelectInput,
  ParamInput,
  InlineNumberInput,
  groupParams,
  CategoryBadge,
} from './NodeEditPopup';

function toTitleCaseFromKey(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getFallbackHowToRead(paramNames: string[], t: (key: string) => string): string {
  const hasTarget = paramNames.some((name) => name.startsWith('target_'));
  const hasLowerUpper = paramNames.includes('lower') || paramNames.includes('upper');
  const hasMin = paramNames.some((name) => name.startsWith('min_'));
  const hasMax = paramNames.some((name) => name.startsWith('max_'));

  if (hasTarget) return t('guidanceFallbackHowToReadTarget');
  if (hasLowerUpper || (hasMin && hasMax)) return t('guidanceFallbackHowToReadRange');
  if (hasMin) return t('guidanceFallbackHowToReadMin');
  if (hasMax) return t('guidanceFallbackHowToReadMax');
  return t('guidanceFallbackHowToReadGeneral');
}

function ConditionNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const tCond = useTranslations('conditions');
  const { conditions, getConditionMeta } = useConditions();
  const { settings } = useUserSettings();
  const nodeData = data as unknown as StrategyNodeData;
  const meta = nodeData.condition_type
    ? getConditionMeta(nodeData.condition_type)
    : null;

  const condKey = nodeData.condition_type || '';
  const label =
    condKey && tCond.has(`${condKey}.label`)
      ? tCond(`${condKey}.label`)
      : (meta?.label || nodeData.label || (condKey ? toTitleCaseFromKey(condKey) : t('condition')));

  const nodeId = useNodeId()!;
  const { getNode, getEdges, setNodes, updateNodeData, deleteElements } = useReactFlow();
  const currentNode = nodeId ? getNode(nodeId) : null;
  const isInsideGroup = !!currentNode?.parentId;

  const [showDesc, setShowDesc] = useState(false);
  const [showInsight, setShowInsight] = useState(false);

  // Check if condition has params configured
  const hasParams = nodeData.params && Object.keys(nodeData.params).length > 0;

  // Collect param entries for tag-style display
  const paramEntries = nodeData.params
    ? Object.entries(nodeData.params)
        .filter(([, v]) => v !== null && v !== undefined)
        .slice(0, 3)
    : [];

  const handleParamChange = useCallback(
    (name: string, value: unknown) => {
      updateNodeData(nodeId, {
        params: { ...nodeData.params, [name]: value },
      });
    },
    [nodeId, nodeData.params, updateNodeData]
  );

  const handleConditionTypeChange = useCallback(
    (key: string) => {
      const condMeta = getConditionMeta(key);
      const defaultParams: Record<string, unknown> = {};
      if (condMeta) {
        for (const p of condMeta.params) {
          defaultParams[p.name] = p.default;
        }
      }

      // Clear this node's stale result + all downstream nodes
      const currentEdges = getEdges();
      const downstream = getDownstreamNodeIds([nodeId], currentEdges);

      setNodes((nds) =>
        nds.map((n) => {
          if (n.id === nodeId) {
            return {
              ...n,
              data: {
                ...n.data,
                condition_type: key,
                params: defaultParams,
                label: condMeta?.label,
                intermediateResult: undefined,
              },
            };
          }
          if (downstream.has(n.id)) {
            const nd = n.data as Record<string, unknown>;
            if (nd.intermediateResult === undefined && nd.resultCount === undefined)
              return n;
            const { intermediateResult: _ir, resultCount: _rc, ...rest } = nd;
            return { ...n, data: rest };
          }
          return n;
        })
      );
    },
    [nodeId, getConditionMeta, getEdges, setNodes]
  );

  const handleDelete = useCallback(() => {
    deleteElements({ nodes: [{ id: nodeId }] });
  }, [nodeId, deleteElements]);

  return (
    <div
      className={`rounded-lg bg-white dark:bg-[#1e1e1f] border min-w-[220px] transition-shadow ${
        selected
          ? 'border-2 border-[#1313ec] shadow-xl'
          : 'border-[#e1e3e5] dark:border-[#2e2e30] shadow-sm hover:shadow-md'
      }`}
    >
      {!isInsideGroup && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-left-[7px] hover:!scale-125 !transition-transform"
        />
      )}
      {isInsideGroup && (
        <Handle
          type="target"
          id="top"
          position={Position.Top}
          className="!w-2.5 !h-2.5 !bg-[#1313ec]/60 !border-2 !border-white dark:!border-[#1e1e1f] !-top-[5px] hover:!scale-125 !transition-transform"
        />
      )}

      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-2 rounded-t-[7px] bg-blue-50 dark:bg-blue-500/10 border-b border-[#e1e3e5] dark:border-[#2e2e30]">
        <div className="flex items-center gap-1.5">
          <Filter className="h-3.5 w-3.5 text-[#1313ec] dark:text-blue-400" />
          <span className="text-[11px] font-bold text-[#1313ec] dark:text-blue-400 uppercase tracking-wider">
            {t('screeningBadge')}
          </span>
        </div>
        {hasParams ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
        ) : (
          <CircleDashed className="h-3.5 w-3.5 text-gray-300 dark:text-gray-600" />
        )}
      </div>

      {/* Content */}
      <div className="px-3 py-2.5">
        <div className="text-[13px] font-bold text-gray-900 dark:text-gray-100">
          {label}
        </div>
        {paramEntries.length > 0 && (
          <div className="mt-2 flex items-center gap-1.5 flex-wrap">
            {paramEntries.map(([k, v]) => (
              <span key={k} className="inline-flex items-center gap-1">
                <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-[10px] text-slate-500">
                  {String(k).replace(/_/g, ' ')}
                </span>
                <span className="px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-[#1313ec] dark:text-blue-400 rounded text-[10px] font-bold">
                  {String(v)}
                </span>
              </span>
            ))}
          </div>
        )}
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

      {!isInsideGroup && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3.5 !h-3.5 !bg-[#1313ec] !border-2 !border-white dark:!border-[#1e1e1f] !-right-[7px] hover:!scale-125 !transition-transform"
        />
      )}
      {isInsideGroup && (
        <Handle
          type="source"
          id="bottom"
          position={Position.Bottom}
          className="!w-2.5 !h-2.5 !bg-[#1313ec]/60 !border-2 !border-white dark:!border-[#1e1e1f] !-bottom-[5px] hover:!scale-125 !transition-transform"
        />
      )}

      {/* Inline edit popup */}
      <NodeEditPopup selected={!!selected} onDelete={handleDelete}>
        <div>
          <FieldLabel>{t('conditionLogic')}</FieldLabel>
          <SelectInput
            value={nodeData.condition_type || ''}
            onChange={handleConditionTypeChange}
          >
            <option value="">{t('selectCondition')}</option>
            {conditions.map((c) => (
              <option key={c.key} value={c.key}>
                {tCond.has(c.key + '.label') ? tCond(c.key + '.label') : (c.label || toTitleCaseFromKey(c.key))}
              </option>
            ))}
          </SelectInput>
        </div>

        {nodeData.condition_type &&
          (() => {
            const currentMeta = getConditionMeta(nodeData.condition_type);
            if (!currentMeta) return null;

            const { paired, standalone } = groupParams(
              currentMeta.params as ConditionParam[]
            );
            const whenToUseKey = currentMeta.key + '.whenToUse';
            const howToReadKey = currentMeta.key + '.howToRead';
            const cautionKey = currentMeta.key + '.caution';
            const fallbackHowToRead = getFallbackHowToRead(
              currentMeta.params.map((p) => p.name),
              t
            );
            const whenToUse = tCond.has(whenToUseKey)
              ? tCond(whenToUseKey)
              : t('guidanceFallbackWhenToUse');
            const howToRead = tCond.has(howToReadKey)
              ? tCond(howToReadKey)
              : fallbackHowToRead;
            const caution = tCond.has(cautionKey)
              ? tCond(cautionKey)
              : t('guidanceFallbackCaution');

            return (
              <>
                {/* Category badge inline with dropdown */}
                {currentMeta.category && (
                  <div className="flex items-center gap-2 flex-wrap -mt-2">
                    <CategoryBadge category={currentMeta.category} />
                  </div>
                )}

                {/* Collapsible description */}
                <button
                  type="button"
                  onClick={() => setShowDesc((prev) => !prev)}
                  className="flex items-center gap-1 text-[11px] text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  {showDesc ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                  {showDesc ? t('hideDescription') : t('showDescription')}
                </button>
                {showDesc && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                    {tCond.has(currentMeta.key + '.desc')
                      ? tCond(currentMeta.key + '.desc')
                      : (currentMeta.description || '')}
                  </p>
                )}

                {/* Params */}
                <div className="space-y-3">
                  {paired.map(([minP, maxP]) => {
                    const suffix = minP.name.replace(/^min_/, '');
                    const isPriceRange = suffix === 'price';
                    return (
                      <div key={`pair-${suffix}`}>
                        <FieldLabel>
                          {t('range')}:{' '}
                          {tCond.has(currentMeta.key + '.params.' + minP.name)
                            ? tCond(currentMeta.key + '.params.' + minP.name)
                            : toTitleCaseFromKey(minP.name)} /{' '}
                          {tCond.has(currentMeta.key + '.params.' + maxP.name)
                            ? tCond(currentMeta.key + '.params.' + maxP.name)
                            : toTitleCaseFromKey(maxP.name)}
                          {isPriceRange ? ` (${settings.baseCurrency})` : ''}
                        </FieldLabel>
                        <div className="flex items-center gap-2">
                          <InlineNumberInput
                            param={minP}
                            value={
                              nodeData.params?.[minP.name] ?? minP.default
                            }
                            onChange={handleParamChange}
                          />
                          <span className="text-gray-400 dark:text-gray-500 text-sm flex-shrink-0">
                            ~
                          </span>
                          <InlineNumberInput
                            param={maxP}
                            value={
                              nodeData.params?.[maxP.name] ?? maxP.default
                            }
                            onChange={handleParamChange}
                          />
                        </div>
                        {isPriceRange && (
                          <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
                            Unit: {settings.baseCurrency}
                          </p>
                        )}
                      </div>
                    );
                  })}

                  {/* 2-column grid for standalone params when 2+ */}
                  <div className={standalone.length >= 2 ? "grid grid-cols-2 gap-3" : "space-y-3"}>
                    {standalone.map((param) => (
                      <ParamInput
                        key={param.name}
                        param={param}
                        value={nodeData.params?.[param.name] ?? param.default}
                        onChange={handleParamChange}
                        conditionKey={currentMeta.key}
                      />
                    ))}
                  </div>
                </div>

                {/* Quick Insight — collapsible, collapsed by default */}
                <div className="rounded-lg bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20">
                  <button
                    type="button"
                    onClick={() => setShowInsight((prev) => !prev)}
                    className="w-full flex items-center justify-between gap-1.5 p-3"
                  >
                    <div className="flex items-center gap-1.5">
                      <Info className="h-3.5 w-3.5 text-[#1313ec] dark:text-blue-400" />
                      <span className="text-xs font-semibold text-[#1313ec] dark:text-blue-400 uppercase">
                        {t('quickInsight')}
                      </span>
                    </div>
                    {showInsight ? (
                      <ChevronUp className="h-3 w-3 text-[#1313ec] dark:text-blue-400" />
                    ) : (
                      <ChevronDown className="h-3 w-3 text-[#1313ec] dark:text-blue-400" />
                    )}
                  </button>
                  {showInsight && (
                    <div className="px-3 pb-3">
                      <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                        {tCond.has(currentMeta.key + '.help')
                          ? tCond(currentMeta.key + '.help')
                          : (currentMeta.description || '')}
                      </p>
                      <div className="mt-2 space-y-1.5 text-[11px] text-gray-600 dark:text-gray-300 leading-relaxed">
                        <p>
                          <span className="font-semibold text-[#1313ec] dark:text-blue-400">
                            {t('guidanceWhenToUse')}:
                          </span>{' '}
                          {whenToUse}
                        </p>
                        <p>
                          <span className="font-semibold text-[#1313ec] dark:text-blue-400">
                            {t('guidanceHowToRead')}:
                          </span>{' '}
                          {howToRead}
                        </p>
                        <p>
                          <span className="font-semibold text-[#1313ec] dark:text-blue-400">
                            {t('guidanceCaution')}:
                          </span>{' '}
                          {caution}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </>
            );
          })()}

      </NodeEditPopup>
    </div>
  );
}

export default memo(ConditionNode);
