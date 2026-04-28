'use client';

import { useState, useEffect, useCallback } from 'react';
import { NodeToolbar, Position, useReactFlow, useNodeId, useStore } from '@xyflow/react';
import { Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ConditionParam } from '@/lib/strategy/conditionRegistry';

function toTitleCaseFromKey(value: string): string {
  return value
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ------------------------------------------------------------------ */
/*  Shared form primitives (extracted from PropertiesPanel)            */
/* ------------------------------------------------------------------ */

export function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-1.5">
      {children}
    </label>
  );
}

export function SelectInput({
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

export const numberInputClass =
  'w-full rounded-lg border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#1e1e1f] px-3 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none focus:border-[#1313ec] focus:ring-1 focus:ring-[#1313ec]/20 transition-colors';

export function ParamInput({
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

  const paramKey = conditionKey + '.params.' + param.name;
  const paramLabel = tCond.has(paramKey) ? tCond(paramKey) : toTitleCaseFromKey(param.name);

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
          <span className="text-gray-600 dark:text-gray-300">
            {Boolean(value) ? tCommon('enabled') : tCommon('disabled')}
          </span>
        </label>
      </div>
    );
  }

  if (param.type === 'ticker') {
    return (
      <div>
        <FieldLabel>{paramLabel}</FieldLabel>
        <input
          type="text"
          value={String(value ?? '')}
          onChange={(e) => onChange(param.name, e.target.value.toUpperCase())}
          placeholder="e.g. AAPL, 005930.KS"
          className={numberInputClass}
        />
      </div>
    );
  }

  if (param.type === 'str') {
    // Generic options-based dropdown
    if (param.options && param.options.length > 0) {
      return (
        <div>
          <FieldLabel>{paramLabel}</FieldLabel>
          <SelectInput
            value={String(value || param.default || '')}
            onChange={(v) => onChange(param.name, v)}
          >
            {param.options.map((opt) => {
              const optKey = `${conditionKey}.options.${param.name}.${opt}`;
              const optLabel = tCond.has(optKey) ? tCond(optKey) : toTitleCaseFromKey(opt);
              return <option key={opt} value={opt}>{optLabel}</option>;
            })}
          </SelectInput>
        </div>
      );
    }
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

  // int or float – use local state so keystrokes aren't blocked by
  // React Flow re-renders; sync to node data on blur.
  return (
    <NumberParamInput
      param={param}
      value={value}
      onChange={onChange}
      label={paramLabel}
    />
  );
}

/** Locally-stateful number input that syncs to node data on blur. */
function NumberParamInput({
  param,
  value,
  onChange,
  label,
}: {
  param: ConditionParam;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
  label: string;
}) {
  const externalStr = value !== null && value !== undefined ? String(value) : '';
  const [local, setLocal] = useState(externalStr);

  // Sync from external when the prop genuinely changes (e.g. condition type switch)
  useEffect(() => {
    setLocal(externalStr);
  }, [externalStr]);

  const flush = () => {
    if (local === '') {
      onChange(param.name, null);
    } else {
      onChange(
        param.name,
        param.type === 'int' ? parseInt(local, 10) : parseFloat(local)
      );
    }
  };

  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <input
        type="number"
        step={param.type === 'float' ? '0.01' : '1'}
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={flush}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            flush();
            (e.target as HTMLInputElement).blur();
          }
        }}
        className={numberInputClass}
      />
    </div>
  );
}

/** Inline number input used inside range rows (no label). */
export function InlineNumberInput({
  param,
  value,
  onChange,
}: {
  param: ConditionParam;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
}) {
  const externalStr = value !== null && value !== undefined ? String(value) : '';
  const [local, setLocal] = useState(externalStr);

  useEffect(() => {
    setLocal(externalStr);
  }, [externalStr]);

  const flush = () => {
    if (local === '') {
      onChange(param.name, null);
    } else {
      onChange(
        param.name,
        param.type === 'int' ? parseInt(local, 10) : parseFloat(local)
      );
    }
  };

  return (
    <input
      type="number"
      step={param.type === 'float' ? '0.01' : '1'}
      value={local}
      placeholder={param.name}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={flush}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          flush();
          (e.target as HTMLInputElement).blur();
        }
      }}
      className={numberInputClass}
    />
  );
}

/**
 * Detect min/max pairs among params.
 * Returns { paired: [minParam, maxParam][], standalone: ConditionParam[] }.
 */
export function groupParams(params: ConditionParam[]) {
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

export function CategoryBadge({ category }: { category: string }) {
  const tCond = useTranslations('conditions');
  const key = `categories.${category}`;
  return (
    <span className="inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
      {tCond.has(key) ? tCond(key) : toTitleCaseFromKey(category)}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Intermediate Result display                                        */
/* ------------------------------------------------------------------ */

export function IntermediateResultSection({
  result,
}: {
  result: import('@/lib/api').NodeIntermediateResult;
}) {
  const t = useTranslations('strategy');
  const tc = useTranslations('conditions');

  // Translate condition labels via i18n, keep others as-is
  const displayLabel =
    result.node_type === 'condition' && tc.has(`${result.label}.label`)
      ? tc(`${result.label}.label`)
      : result.label;

  return (
    <div className="pt-3 border-t border-[#e1e3e5] dark:border-[#2e2e30]">
      <FieldLabel>{t('intermediateResults')}</FieldLabel>

      <div className="rounded-lg bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 p-3 mb-3">
        <div className="text-[11px] font-semibold text-[#1313ec] dark:text-blue-400 uppercase tracking-wider">
          {t('intermediateResultsFor', { label: displayLabel })}
        </div>
        <div className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
          {result.stock_count.toLocaleString()}
          <span className="text-sm font-normal text-gray-500 ml-1">
            {t('stockCount')}
          </span>
        </div>
      </div>

      {result.node_type === 'universe' && (
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-2">
          {t('universeNote')}
        </p>
      )}

      {result.stocks.length > 0 && (
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
              {result.stocks.slice(0, 20).map((stock, i) => (
                <tr
                  key={stock.ticker}
                  className="border-t border-[#e1e3e5] dark:border-[#2e2e30]"
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
          {result.stocks.length > 20 && (
            <div className="px-3 py-2 text-[10px] text-gray-400 text-center border-t border-[#e1e3e5] dark:border-[#2e2e30]">
              {t('andMore', { count: result.stocks.length - 20 })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** Small badge shown on the node body when intermediate results exist. */
export function MatchedCountBadge({
  count,
}: {
  count: number;
}) {
  const t = useTranslations('strategy');
  return (
    <div className="mt-1.5 flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
      {count.toLocaleString()} {t('stockCount')}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  NodeEditPopup wrapper                                              */
/* ------------------------------------------------------------------ */

interface NodeEditPopupProps {
  selected: boolean;
  children: React.ReactNode;
  onDelete?: () => void;
}

export default function NodeEditPopup({
  selected,
  children,
  onDelete,
}: NodeEditPopupProps) {
  const t = useTranslations('strategy');
  const nodeId = useNodeId();
  const { setNodes } = useReactFlow();
  const zoom = useStore((s) => s.transform[2]);
  // Scale popup proportionally with canvas zoom; clamp so it never gets too tiny
  const popupScale = Math.min(1, Math.max(0.5, zoom));

  // Escape key deselects node (closes popup)
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selected) {
        setNodes((nds) =>
          nds.map((n) =>
            n.id === nodeId ? { ...n, selected: false } : n
          )
        );
      }
    },
    [selected, nodeId, setNodes]
  );

  useEffect(() => {
    if (selected) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [selected, handleKeyDown]);

  return (
    <NodeToolbar
      isVisible={selected}
      position={Position.Bottom}
      offset={12}
      align="center"
    >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
      <div
        className="nodrag nowheel nopan w-[360px] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e30] bg-white dark:bg-[#0b0b0c] shadow-xl"
        style={{ transform: `scale(${popupScale})`, transformOrigin: 'top center' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 space-y-4 max-h-[480px] overflow-y-auto">
          {children}
        </div>
        {onDelete && (
          <div className="px-4 py-2.5 border-t border-[#e1e3e5] dark:border-[#2e2e30]">
            <button
              type="button"
              onClick={onDelete}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t('removeNode')}
            </button>
          </div>
        )}
      </div>
    </NodeToolbar>
  );
}
