'use client';

import { memo, useCallback } from 'react';
import { Handle, Position, useNodeId, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Filter, CheckCircle2, CircleDashed, Info } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { getDownstreamNodeIds, type StrategyNodeData } from '@/lib/strategy/graphSerializer';
import type { ConditionParam } from '@/lib/strategy/conditionRegistry';
import { useConditions } from '@/contexts/ConditionsContext';
import NodeEditPopup, {
  FieldLabel,
  SelectInput,
  ParamInput,
  InlineNumberInput,
  groupParams,
  CategoryBadge,
} from './NodeEditPopup';

function ConditionNode({ data, selected }: NodeProps) {
  const t = useTranslations('strategy');
  const tCond = useTranslations('conditions');
  const { conditions, getConditionMeta } = useConditions();
  const nodeData = data as unknown as StrategyNodeData;
  const meta = nodeData.condition_type
    ? getConditionMeta(nodeData.condition_type)
    : null;

  const condKey = nodeData.condition_type || '';
  let label: string;
  if (condKey) {
    try {
      label = tCond(`${condKey}.label`);
    } catch {
      label = meta?.label || nodeData.label || t('condition');
    }
  } else {
    label = nodeData.label || t('condition');
  }

  const nodeId = useNodeId()!;
  const { getNode, getEdges, setNodes, updateNodeData, deleteElements } = useReactFlow();
  const currentNode = nodeId ? getNode(nodeId) : null;
  const isInsideGroup = !!currentNode?.parentId;

  // Check if condition has params configured
  const hasParams = nodeData.params && Object.keys(nodeData.params).length > 0;

  // Build a concise value summary (e.g., "RSI < 30" or "Period: 20")
  const valueSummary = nodeData.params
    ? Object.entries(nodeData.params)
        .filter(([, v]) => v !== null && v !== undefined)
        .slice(0, 2)
        .map(([k, v]) => `${String(k).replace(/_/g, ' ')}: ${v}`)
        .join(' · ')
    : '';

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
            const { intermediateResult, resultCount, ...rest } = nd;
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
      className={`rounded-xl bg-white dark:bg-[#1e1e1f] border min-w-[220px] transition-shadow ${
        selected
          ? 'border-[#1313ec] shadow-[0_0_0_1px_#1313ec] ring-1 ring-[#1313ec]/20'
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
      <div className="flex items-center justify-between px-3 py-1.5 rounded-t-[10px] bg-blue-50 dark:bg-blue-500/10 border-b border-blue-100 dark:border-blue-500/20">
        <div className="flex items-center gap-1.5">
          <Filter className="h-3 w-3 text-[#1313ec] dark:text-blue-400" />
          <span className="text-[10px] font-semibold text-[#1313ec] dark:text-blue-400 uppercase tracking-wider">
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
        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {label}
        </div>
        {valueSummary && (
          <div className="mt-1.5 text-[11px] text-gray-500 dark:text-gray-400 font-mono bg-gray-50 dark:bg-gray-800/50 px-2 py-1 rounded-md">
            {valueSummary}
          </div>
        )}
      </div>

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
                {tCond(c.key + '.label')}
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

            return (
              <>
                {currentMeta.category && (
                  <div className="flex items-center gap-2">
                    <CategoryBadge category={currentMeta.category} />
                  </div>
                )}

                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                  {tCond(currentMeta.key + '.desc')}
                </p>

                <div className="space-y-3">
                  {paired.map(([minP, maxP]) => {
                    const suffix = minP.name.replace(/^min_/, '');
                    return (
                      <div key={`pair-${suffix}`}>
                        <FieldLabel>
                          {t('range')}:{' '}
                          {tCond(currentMeta.key + '.params.' + minP.name)} /{' '}
                          {tCond(currentMeta.key + '.params.' + maxP.name)}
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
                      </div>
                    );
                  })}

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

                {/* Quick Insight */}
                <div className="rounded-lg bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 p-3">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Info className="h-3.5 w-3.5 text-[#1313ec] dark:text-blue-400" />
                    <span className="text-xs font-semibold text-[#1313ec] dark:text-blue-400 uppercase">
                      {t('quickInsight')}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                    {tCond(currentMeta.key + '.help')}
                  </p>
                </div>
              </>
            );
          })()}

      </NodeEditPopup>
    </div>
  );
}

export default memo(ConditionNode);
