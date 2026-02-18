'use client';

import type { Node } from '@xyflow/react';
import { X, Info, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { StrategyNodeData } from '@/lib/strategy/graphSerializer';
import { useConditions } from '@/contexts/ConditionsContext';
import type { ConditionParam } from '@/lib/strategy/conditionRegistry';
import type { NodeIntermediateResult } from '@/lib/api';

const UNIVERSES = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ100'];

interface PropertiesPanelProps {
  node: Node<StrategyNodeData> | null;
  onUpdate: (nodeId: string, data: Partial<StrategyNodeData>) => void;
  onClose: () => void;
  onDeleteNode?: (nodeId: string) => void;
  intermediateResult?: NodeIntermediateResult;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">
      {children}
    </label>
  );
}

function SelectInput({
  value,
  onChange,
  children,
}: {
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none focus:border-[#1313ec] focus:ring-1 focus:ring-[#1313ec]/20 transition-colors"
    >
      {children}
    </select>
  );
}

const numberInputClass =
  'w-full rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none focus:border-[#1313ec] focus:ring-1 focus:ring-[#1313ec]/20 transition-colors';

function ParamInput({
  param,
  value,
  onChange,
  conditionKey,
}: {
  param: ConditionParam;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
  conditionKey: string;
}) {
  const tCond = useTranslations('conditions');
  const tCommon = useTranslations('common');

  const paramLabel = tCond(conditionKey + '.params.' + param.name);

  if (param.type === 'bool') {
    return (
      <div>
        <FieldLabel>{paramLabel}</FieldLabel>
        <label className="flex items-center gap-2.5 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => onChange(param.name, e.target.checked)}
            className="rounded border-[#e1e3e5] dark:border-[#2e2e30] text-[#1313ec] focus:ring-[#1313ec]/20"
          />
          <span className="text-gray-600 dark:text-gray-300">{Boolean(value) ? tCommon('enabled') : tCommon('disabled')}</span>
        </label>
      </div>
    );
  }

  if (param.type === 'str') {
    if (param.name === 'direction') {
      return (
        <div>
          <FieldLabel>{paramLabel}</FieldLabel>
          <SelectInput
            value={String(value || param.default || '')}
            onChange={(v) => onChange(param.name, v)}
          >
            <option value="up">{tCommon('up')}</option>
            <option value="down">{tCommon('down')}</option>
          </SelectInput>
        </div>
      );
    }
    if (param.name === 'condition') {
      return (
        <div>
          <FieldLabel>{paramLabel}</FieldLabel>
          <SelectInput
            value={String(value || param.default || '')}
            onChange={(v) => onChange(param.name, v)}
          >
            <option value="below">{tCommon('below')}</option>
            <option value="above">{tCommon('above')}</option>
          </SelectInput>
        </div>
      );
    }
    return (
      <div>
        <FieldLabel>{paramLabel}</FieldLabel>
        <input
          type="text"
          value={String(value ?? '')}
          onChange={(e) => onChange(param.name, e.target.value)}
          className={numberInputClass}
        />
      </div>
    );
  }

  // int or float
  return (
    <div>
      <FieldLabel>{paramLabel}</FieldLabel>
      <input
        type="number"
        step={param.type === 'float' ? '0.01' : '1'}
        value={value !== null && value !== undefined ? String(value) : ''}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === '') {
            onChange(param.name, null);
          } else {
            onChange(
              param.name,
              param.type === 'int' ? parseInt(raw, 10) : parseFloat(raw)
            );
          }
        }}
        className={numberInputClass}
      />
    </div>
  );
}

/** Inline number input used inside range rows (no label). */
function InlineNumberInput({
  param,
  value,
  onChange,
}: {
  param: ConditionParam;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
}) {
  return (
    <input
      type="number"
      step={param.type === 'float' ? '0.01' : '1'}
      value={value !== null && value !== undefined ? String(value) : ''}
      placeholder={param.name}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === '') {
          onChange(param.name, null);
        } else {
          onChange(
            param.name,
            param.type === 'int' ? parseInt(raw, 10) : parseFloat(raw)
          );
        }
      }}
      className={numberInputClass}
    />
  );
}

/**
 * Detect min/max pairs among params.
 * Returns { paired: [minParam, maxParam][], standalone: ConditionParam[] }.
 *
 * Matching heuristic: two params whose names share a common suffix and
 * one starts with "min_" while the other starts with "max_"
 * (e.g. min_pe / max_pe, min_yield / max_yield).
 */
function groupParams(params: ConditionParam[]) {
  const paired: [ConditionParam, ConditionParam][] = [];
  const consumed = new Set<string>();

  for (const p of params) {
    if (consumed.has(p.name)) continue;
    const minMatch = p.name.match(/^min_(.+)$/);
    if (minMatch) {
      const suffix = minMatch[1];
      const maxParam = params.find((q) => q.name === `max_${suffix}`);
      if (maxParam && !consumed.has(maxParam.name)) {
        paired.push([p, maxParam]);
        consumed.add(p.name);
        consumed.add(maxParam.name);
        continue;
      }
    }
  }

  const standalone = params.filter((p) => !consumed.has(p.name));
  return { paired, standalone };
}

function CategoryBadge({ category }: { category: string }) {
  const tCond = useTranslations('conditions');
  return (
    <span className="inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
      {tCond(`categories.${category}`)}
    </span>
  );
}

export default function PropertiesPanel({
  node,
  onUpdate,
  onClose,
  onDeleteNode,
  intermediateResult,
}: PropertiesPanelProps) {
  const t = useTranslations('strategy');
  const tCond = useTranslations('conditions');
  const { conditions, getConditionMeta } = useConditions();

  if (!node) return null;

  const nodeData = node.data;

  const handleParamChange = (name: string, value: unknown) => {
    onUpdate(node.id, {
      params: { ...nodeData.params, [name]: value },
    });
  };

  return (
    <div className="w-80 h-full border-l border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e30] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {t('nodeProperties')}
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <X className="h-4 w-4 text-gray-400" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Universe node */}
        {nodeData.node_type === 'universe' && (
          <>
            <div>
              <FieldLabel>{t('displayName')}</FieldLabel>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-[#1e1e1f] px-3 py-2 rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30]">
                {t('marketSelection')}
              </div>
            </div>
            <div>
              <FieldLabel>{t('stockUniverse')}</FieldLabel>
              <SelectInput
                value={nodeData.universe || 'KOSPI'}
                onChange={(v) => onUpdate(node.id, { universe: v })}
              >
                {UNIVERSES.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </SelectInput>
            </div>
          </>
        )}

        {/* Condition node */}
        {nodeData.node_type === 'condition' && (
          <>
            <div>
              <FieldLabel>{t('displayName')}</FieldLabel>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-[#1e1e1f] px-3 py-2 rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30]">
                {nodeData.condition_type
                  ? tCond(nodeData.condition_type + '.label')
                  : t('condition')}
              </div>
            </div>
            <div>
              <FieldLabel>{t('conditionLogic')}</FieldLabel>
              <SelectInput
                value={nodeData.condition_type || ''}
                onChange={(key) => {
                  const meta = getConditionMeta(key);
                  const defaultParams: Record<string, unknown> = {};
                  if (meta) {
                    for (const p of meta.params) {
                      defaultParams[p.name] = p.default;
                    }
                  }
                  onUpdate(node.id, {
                    condition_type: key,
                    params: defaultParams,
                    label: meta?.label,
                  });
                }}
              >
                <option value="">{t('selectCondition')}</option>
                {conditions.map((c) => (
                  <option key={c.key} value={c.key}>
                    {tCond(c.key + '.label')}
                  </option>
                ))}
              </SelectInput>
            </div>

            {nodeData.condition_type && (() => {
              const meta = getConditionMeta(nodeData.condition_type);
              if (!meta) return null;

              const { paired, standalone } = groupParams(meta.params as ConditionParam[]);

              return (
                <>
                  {/* Category badge + description */}
                  {meta.category && (
                    <div className="flex items-center gap-2">
                      <CategoryBadge category={meta.category} />
                    </div>
                  )}

                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                    {tCond(meta.key + '.desc')}
                  </p>

                  <div className="space-y-4">
                    {/* Render paired min/max params side by side */}
                    {paired.map(([minP, maxP]) => {
                      const suffix = minP.name.replace(/^min_/, '');
                      return (
                        <div key={`pair-${suffix}`}>
                          <FieldLabel>{t('range')}: {tCond(meta.key + '.params.' + minP.name)} / {tCond(meta.key + '.params.' + maxP.name)}</FieldLabel>
                          <div className="flex items-center gap-2">
                            <InlineNumberInput
                              param={minP}
                              value={nodeData.params?.[minP.name] ?? minP.default}
                              onChange={handleParamChange}
                            />
                            <span className="text-gray-400 dark:text-gray-500 text-sm flex-shrink-0">~</span>
                            <InlineNumberInput
                              param={maxP}
                              value={nodeData.params?.[maxP.name] ?? maxP.default}
                              onChange={handleParamChange}
                            />
                          </div>
                        </div>
                      );
                    })}

                    {/* Render standalone params normally */}
                    {standalone.map((param) => (
                      <ParamInput
                        key={param.name}
                        param={param}
                        value={nodeData.params?.[param.name] ?? param.default}
                        onChange={handleParamChange}
                        conditionKey={meta.key}
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
                      {tCond(meta.key + '.desc')}
                    </p>
                  </div>
                </>
              );
            })()}
          </>
        )}

        {/* Logic / Group node */}
        {nodeData.node_type === 'logic' && (
          <>
            <div>
              <FieldLabel>{t('displayName')}</FieldLabel>
              <div className="text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-[#1e1e1f] px-3 py-2 rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30]">
                {t(
                  nodeData.logic_operator === 'or'
                    ? 'orGroup'
                    : nodeData.logic_operator === 'not'
                      ? 'notGroup'
                      : 'andGroup'
                )}
              </div>
            </div>
            <div>
              <FieldLabel>{t('logicOperator')}</FieldLabel>
              <SelectInput
                value={nodeData.logic_operator || 'and'}
                onChange={(v) => onUpdate(node.id, { logic_operator: v })}
              >
                <option value="and">{t('andAllMustMatch')}</option>
                <option value="or">{t('orAnyMustMatch')}</option>
                <option value="not">{t('notInvertFirst')}</option>
              </SelectInput>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
              {t('groupInstruction')}
            </div>
          </>
        )}

        {/* Output node */}
        {nodeData.node_type === 'output' && (
          <div className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
            {t('outputInstruction')}
          </div>
        )}

        {/* Intermediate Results */}
        {intermediateResult && (
          <div className="mt-2 pt-4 border-t border-[#e1e3e5] dark:border-[#2e2e30]">
            <FieldLabel>{t('intermediateResults')}</FieldLabel>

            <div className="rounded-lg bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 p-3 mb-3">
              <div className="text-[11px] font-semibold text-[#1313ec] dark:text-blue-400 uppercase tracking-wider">
                {t('intermediateResultsFor', { label: intermediateResult.label })}
              </div>
              <div className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
                {intermediateResult.stock_count.toLocaleString()}
                <span className="text-sm font-normal text-gray-500 ml-1">{t('stockCount')}</span>
              </div>
            </div>

            {intermediateResult.node_type === 'universe' && (
              <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-2">
                {t('universeNote')}
              </p>
            )}

            {intermediateResult.stocks.length > 0 && (
              <div className="rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-gray-800/50 text-[10px] text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                      <th className="px-2 py-1.5 text-left">#</th>
                      <th className="px-2 py-1.5 text-left">{t('ticker')}</th>
                      <th className="px-2 py-1.5 text-left">{t('name')}</th>
                      <th className="px-2 py-1.5 text-right">{t('price')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {intermediateResult.stocks.slice(0, 50).map((stock, i) => (
                      <tr
                        key={stock.ticker}
                        className="border-t border-[#e1e3e5] dark:border-[#2e2e30] hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                      >
                        <td className="px-2 py-1 text-gray-400">{i + 1}</td>
                        <td className="px-2 py-1 font-mono text-[#1313ec] font-medium text-[11px]">
                          {stock.ticker}
                        </td>
                        <td className="px-2 py-1 text-gray-700 dark:text-gray-200 truncate max-w-[80px]">
                          {stock.name}
                        </td>
                        <td className="px-2 py-1 text-right text-gray-600 dark:text-gray-300">
                          {stock.current_price?.toLocaleString() ?? '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {intermediateResult.stocks.length > 50 && (
                  <div className="px-3 py-2 text-[10px] text-gray-400 text-center border-t border-[#e1e3e5] dark:border-[#2e2e30]">
                    {t('andMore', { count: intermediateResult.stocks.length - 50 })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom actions */}
      <div className="px-4 py-3 border-t border-[#e1e3e5] dark:border-[#2e2e30] flex justify-between items-center">
        <button
          type="button"
          onClick={() => onDeleteNode?.(node.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {t('removeNode')}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-1.5 text-xs font-medium rounded-lg bg-[#1313ec] text-white hover:bg-[#1010c0] transition-colors"
        >
          {t('applyChanges')}
        </button>
      </div>
    </div>
  );
}
