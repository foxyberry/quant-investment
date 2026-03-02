'use client';

import { useState, useCallback, useEffect } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { X, Plus, Trash2, Power, PowerOff } from 'lucide-react';
import { Button } from '@/components/ui';
import { getSellRules, createSellRule, updateSellRule, deleteSellRule } from '@/lib/api';
import type { Holding, SellRule, SellRuleType } from '@/lib/types';
import { formatCurrency as formatCurrencyUtil } from '@/lib/format';

interface SellRuleModalProps {
  isOpen: boolean;
  holding: Holding | null;
  onClose: () => void;
  onRulesChanged: () => void;
}

const RULE_TYPES: SellRuleType[] = ['stop_loss', 'take_profit', 'trailing_stop', 'holding_period'];

export default function SellRuleModal({
  isOpen,
  holding,
  onClose,
  onRulesChanged,
}: SellRuleModalProps) {
  const t = useTranslations('portfolio');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency?: string) =>
    formatCurrencyUtil(value, currency, locale);

  const [rules, setRules] = useState<SellRule[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New rule form
  const [newRuleType, setNewRuleType] = useState<SellRuleType>('stop_loss');
  const [newRuleValue, setNewRuleValue] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  // Load rules when modal opens
  useEffect(() => {
    if (isOpen && holding) {
      setError(null);
      setNewRuleValue('');
      setIsLoading(true);
      getSellRules(holding.ticker)
        .then(setRules)
        .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load rules'))
        .finally(() => setIsLoading(false));
    }
  }, [isOpen, holding]);

  // Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const getParamKey = (ruleType: SellRuleType): string =>
    ruleType === 'holding_period' ? 'max_days' : 'pct';

  const getParamLabel = (ruleType: SellRuleType): string => {
    if (ruleType === 'holding_period') return t('sellRuleDays');
    return '%';
  };

  const handleAddRule = useCallback(async () => {
    if (!holding || !newRuleValue.trim()) return;
    const val = parseFloat(newRuleValue);
    if (isNaN(val) || val <= 0) return;

    setIsAdding(true);
    setError(null);
    try {
      const paramKey = getParamKey(newRuleType);
      const paramValue = newRuleType === 'holding_period' ? Math.floor(val) : val;
      const created = await createSellRule(holding.ticker, {
        rule_type: newRuleType,
        params: { [paramKey]: paramValue },
      });
      setRules((prev) => [...prev, created]);
      setNewRuleValue('');
      onRulesChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create rule');
    } finally {
      setIsAdding(false);
    }
  }, [holding, newRuleType, newRuleValue, onRulesChanged, t]);

  const handleToggleActive = useCallback(async (rule: SellRule) => {
    try {
      const updated = await updateSellRule(rule.id, { is_active: !rule.is_active });
      setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      onRulesChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update rule');
    }
  }, [onRulesChanged]);

  const handleDeleteRule = useCallback(async (ruleId: number) => {
    try {
      await deleteSellRule(ruleId);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
      onRulesChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete rule');
    }
  }, [onRulesChanged]);

  const getRuleTypeLabel = (ruleType: string): string => {
    const key = `sellRule_${ruleType}` as const;
    try { return t(key); } catch { return ruleType; }
  };

  const getRuleValueDisplay = (rule: SellRule): string => {
    if (rule.rule_type === 'holding_period') {
      return `${rule.params.max_days} ${t('sellRuleDays')}`;
    }
    return `${rule.params.pct}%`;
  };

  if (!isOpen || !holding) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sell-rule-modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <h2
            id="sell-rule-modal-title"
            className="text-lg font-semibold text-[var(--foreground)]"
          >
            {t('sellRuleTitle')}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Holding info banner */}
        <div className="border-b border-[var(--border)] bg-[var(--background)]/50 px-6 py-3">
          <p className="text-sm font-medium text-[var(--foreground)]">
            <span className="font-mono text-[var(--color-primary)]">
              {holding.ticker}
            </span>
            {holding.name && (
              <span className="text-[var(--foreground-muted)]">
                {' '}&mdash; {holding.name}
              </span>
            )}
          </p>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--foreground-muted)]">
            <span>{t('quantity')}: {holding.quantity}</span>
            <span>{t('avgPrice')}: {formatCurrency(holding.avg_price, holding.currency)}</span>
            {holding.pnl_pct !== null && (
              <span className={holding.pnl_pct >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                {t('pnl')}: {holding.pnl_pct >= 0 ? '+' : ''}{holding.pnl_pct.toFixed(2)}%
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Existing rules */}
          {isLoading ? (
            <div className="py-8 text-center text-sm text-[var(--foreground-muted)]">
              {t('loading')}
            </div>
          ) : rules.length === 0 ? (
            <div className="py-6 text-center text-sm text-[var(--foreground-muted)]">
              {t('sellRuleEmpty')}
            </div>
          ) : (
            <div className="space-y-2 mb-4">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className={`flex items-center justify-between rounded-lg border px-4 py-3 ${
                    rule.is_active
                      ? 'border-[var(--border)] bg-[var(--background)]'
                      : 'border-[var(--border)] bg-[var(--background)] opacity-50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      rule.rule_type === 'stop_loss' ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300' :
                      rule.rule_type === 'take_profit' ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' :
                      rule.rule_type === 'trailing_stop' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300' :
                      'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                    }`}>
                      {getRuleTypeLabel(rule.rule_type)}
                    </span>
                    <span className="text-sm font-mono text-[var(--foreground)]">
                      {getRuleValueDisplay(rule)}
                    </span>
                    {rule.triggered_at && (
                      <span className="text-xs text-orange-600 dark:text-orange-400">
                        {t('sellRuleTriggered')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleToggleActive(rule)}
                      className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
                      aria-label={rule.is_active ? t('sellRuleDeactivate') : t('sellRuleActivate')}
                      title={rule.is_active ? t('sellRuleDeactivate') : t('sellRuleActivate')}
                    >
                      {rule.is_active ? <Power className="h-4 w-4" /> : <PowerOff className="h-4 w-4" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteRule(rule.id)}
                      className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/50 dark:hover:text-red-400 transition-colors"
                      aria-label={`Delete rule`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add new rule form */}
          <div className="border-t border-[var(--border)] pt-4">
            <p className="text-sm font-medium text-[var(--foreground)] mb-3">
              {t('sellRuleAdd')}
            </p>
            <div className="flex gap-2">
              <select
                value={newRuleType}
                onChange={(e) => setNewRuleType(e.target.value as SellRuleType)}
                className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--foreground)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                disabled={isAdding}
              >
                {RULE_TYPES.map((rt) => (
                  <option key={rt} value={rt}>{getRuleTypeLabel(rt)}</option>
                ))}
              </select>
              <div className="relative flex-1">
                <input
                  type="number"
                  value={newRuleValue}
                  onChange={(e) => setNewRuleValue(e.target.value)}
                  placeholder={newRuleType === 'holding_period' ? '30' : '10'}
                  min="0"
                  step="any"
                  className="w-full rounded-lg border border-[var(--border)] px-3 py-2 pr-8 text-sm text-[var(--foreground)] placeholder-[var(--foreground-muted)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                  disabled={isAdding}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddRule(); } }}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-[var(--foreground-muted)]">
                  {getParamLabel(newRuleType)}
                </span>
              </div>
              <Button
                type="button"
                variant="primary"
                onClick={handleAddRule}
                disabled={isAdding || !newRuleValue.trim()}
                className="shrink-0"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-[var(--border)] px-6 py-4">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            className="w-full"
          >
            {t('done')}
          </Button>
        </div>
      </div>
    </div>
  );
}
