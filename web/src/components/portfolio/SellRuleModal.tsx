'use client';

import { useEffect, useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Plus, Trash2, X, Shield, Save, BookMarked } from 'lucide-react';
import { Button } from '@/components/ui';
import {
  getSellRules,
  createSellRule,
  updateSellRule,
  deleteSellRule,
  getSellRulePresets,
  applySellRulePreset,
  saveAsPreset,
} from '@/lib/api';
import type { Holding, SellRule, SellRuleCreate, SellRuleType, SellRulePreset } from '@/lib/types';

interface SellRuleModalProps {
  holding: Holding;
  onClose: () => void;
  onUpdate: () => void;
}

type TabMode = 'manual' | 'preset';

const RULE_TYPES: SellRuleType[] = ['stop_loss', 'take_profit', 'trailing_stop', 'holding_period'];

export default function SellRuleModal({ holding, onClose, onUpdate }: SellRuleModalProps) {
  const t = useTranslations('portfolio');
  const [rules, setRules] = useState<SellRule[]>([]);
  const [loading, setLoading] = useState(true);

  // Tab state
  const [activeTab, setActiveTab] = useState<TabMode>('manual');

  // Preset state
  const [presets, setPresets] = useState<SellRulePreset[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(false);
  const [presetsLoaded, setPresetsLoaded] = useState(false);
  const [presetError, setPresetError] = useState<string | null>(null);

  // New rule form
  const [newRuleType, setNewRuleType] = useState<SellRuleType>('stop_loss');
  const [newRuleValue, setNewRuleValue] = useState('');
  const [addError, setAddError] = useState<string | null>(null);
  const [isMutating, setIsMutating] = useState(false);

  // Save-as-preset feedback
  const [savePresetMsg, setSavePresetMsg] = useState<string | null>(null);

  const fetchRules = useCallback(async () => {
    try {
      const data = await getSellRules(holding.ticker);
      setRules(data);
    } catch {
      // Fail silently
    } finally {
      setLoading(false);
    }
  }, [holding.ticker]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const fetchPresets = useCallback(async () => {
    if (presetsLoaded) return;
    setPresetsLoading(true);
    try {
      const data = await getSellRulePresets();
      setPresets(data);
      setPresetsLoaded(true);
    } catch {
      // Fail silently
    } finally {
      setPresetsLoading(false);
    }
  }, [presetsLoaded]);

  // Lazy-load presets when preset tab is first selected
  useEffect(() => {
    if (activeTab === 'preset') {
      fetchPresets();
    }
  }, [activeTab, fetchPresets]);

  const paramLabel = (type: SellRuleType): string => {
    if (type === 'holding_period') return t('sellRuleMaxDays');
    return t('sellRulePercent');
  };

  const paramPlaceholder = (type: SellRuleType): string => {
    switch (type) {
      case 'stop_loss': return '-10';
      case 'take_profit': return '20';
      case 'trailing_stop': return '8';
      case 'holding_period': return '90';
    }
  };

  const buildParams = (type: SellRuleType, value: number): Record<string, unknown> => {
    if (type === 'holding_period') return { max_days: Math.round(value) };
    if (type === 'stop_loss') return { pct: value > 0 ? -value : value };
    return { pct: Math.abs(value) };
  };

  const validateValue = (type: SellRuleType, value: number): string | null => {
    if (!Number.isFinite(value) || value === 0) return t('sellRuleInvalidValue');
    if (type === 'holding_period' && (value < 1 || !Number.isInteger(value))) {
      return t('sellRuleMaxDaysPositive');
    }
    return null;
  };

  const handleAdd = async () => {
    const val = parseFloat(newRuleValue);
    const error = validateValue(newRuleType, val);
    if (error) {
      setAddError(error);
      return;
    }

    setAddError(null);
    setIsMutating(true);
    const data: SellRuleCreate = {
      rule_type: newRuleType,
      params: buildParams(newRuleType, val),
    };

    try {
      await createSellRule(holding.ticker, data);
      setNewRuleValue('');
      await fetchRules();
      onUpdate();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : t('sellRuleAddFailed'));
    } finally {
      setIsMutating(false);
    }
  };

  const handleToggle = async (rule: SellRule) => {
    setIsMutating(true);
    try {
      await updateSellRule(rule.id, { is_active: !rule.is_active });
      await fetchRules();
      onUpdate();
    } catch {
      // Fail silently
    } finally {
      setIsMutating(false);
    }
  };

  const handleDelete = async (ruleId: number) => {
    setIsMutating(true);
    try {
      await deleteSellRule(ruleId);
      await fetchRules();
      onUpdate();
    } catch {
      // Fail silently
    } finally {
      setIsMutating(false);
    }
  };

  const handleApplyPreset = async (presetId: number) => {
    setIsMutating(true);
    setPresetError(null);
    try {
      await applySellRulePreset(holding.ticker, presetId);
      await fetchRules();
      onUpdate();
    } catch {
      setPresetError(t('sellRulePresetApplyFailed'));
    } finally {
      setIsMutating(false);
    }
  };

  const handleSaveAsPreset = async () => {
    const name = window.prompt(t('saveAsPresetName'));
    if (!name || !name.trim()) return;

    setIsMutating(true);
    setSavePresetMsg(null);
    try {
      await saveAsPreset(holding.ticker, name.trim());
      setSavePresetMsg(t('saveAsPresetSuccess'));
      // Refresh presets if they were loaded
      if (presetsLoaded) {
        setPresetsLoaded(false);
        const data = await getSellRulePresets();
        setPresets(data);
        setPresetsLoaded(true);
      }
    } catch {
      setSavePresetMsg(t('saveAsPresetFailed'));
    } finally {
      setIsMutating(false);
    }
  };

  const ruleTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      stop_loss: t('stopLoss'),
      take_profit: t('takeProfit'),
      trailing_stop: t('trailingStop'),
      holding_period: t('holdingPeriod'),
    };
    return labels[type] || type;
  };

  const ruleTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      stop_loss: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      take_profit: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      trailing_stop: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      holding_period: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    };
    return colors[type] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
  };

  const formatRuleValue = (rule: SellRule) => {
    if (rule.rule_type === 'holding_period') {
      const maxDays = rule.params?.max_days;
      return maxDays != null ? `${maxDays} ${t('sellRuleDays')}` : '--';
    }
    const pct = rule.params?.pct;
    return pct != null ? `${Number(pct) > 0 ? '+' : ''}${pct}%` : '--';
  };

  const isPresetApplied = (presetId: number): boolean => {
    return rules.some((r) => r.preset_id === presetId);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="mx-4 w-full max-w-lg rounded-xl bg-[var(--background-secondary)] shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-red-100 p-2 dark:bg-red-900/30">
              <Shield className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[var(--foreground)]">
                {t('sellRulesTitle')} - {holding.ticker}
              </h2>
              {holding.name && (
                <p className="text-sm text-[var(--foreground-muted)]">{holding.name}</p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-[var(--foreground-muted)] hover:bg-[var(--background)] transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Rules List */}
        <div className="max-h-64 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="space-y-2 animate-pulse">
              <div className="h-10 rounded bg-[var(--border)]" />
              <div className="h-10 rounded bg-[var(--border)]" />
            </div>
          ) : rules.length === 0 ? (
            <p className="text-center text-sm text-[var(--foreground-muted)] py-4">
              {t('noSellRules')}
            </p>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ruleTypeColor(rule.rule_type)}`}>
                      {ruleTypeLabel(rule.rule_type)}
                    </span>
                    <span className="text-sm font-mono text-[var(--foreground)]">
                      {formatRuleValue(rule)}
                    </span>
                    {rule.preset_id != null && (
                      <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        <BookMarked className="inline h-3 w-3 mr-0.5" />
                        {t('sellRuleFromPreset')}
                      </span>
                    )}
                    {rule.triggered_at && (
                      <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                        {t('sellRuleTriggered')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleToggle(rule)}
                      disabled={isMutating}
                      className={`rounded-full px-2 py-0.5 text-xs font-medium transition-colors disabled:opacity-50 ${
                        rule.is_active
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500'
                      }`}
                    >
                      {rule.is_active ? t('sellRuleActive') : t('sellRuleInactive')}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(rule.id)}
                      disabled={isMutating}
                      className="rounded-md p-1 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Tab Buttons */}
        <div className="flex border-t border-[var(--border)] px-6 pt-3">
          <button
            type="button"
            onClick={() => setActiveTab('manual')}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === 'manual'
                ? 'bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] border-b-transparent'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            <Plus className="inline h-3.5 w-3.5 mr-1" />
            {t('sellRuleManualInput')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('preset')}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === 'preset'
                ? 'bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] border-b-transparent'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            <BookMarked className="inline h-3.5 w-3.5 mr-1" />
            {t('sellRulePresets')}
          </button>
        </div>

        {/* Tab Content */}
        <div className="px-6 py-4">
          {activeTab === 'manual' ? (
            /* Manual Input Tab */
            <div>
              <p className="text-sm font-medium text-[var(--foreground)] mb-2">{t('addSellRule')}</p>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <label className="block text-xs text-[var(--foreground-muted)] mb-1">{t('sellRuleType')}</label>
                  <select
                    value={newRuleType}
                    onChange={(e) => {
                      setNewRuleType(e.target.value as SellRuleType);
                      setNewRuleValue('');
                      setAddError(null);
                    }}
                    className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                  >
                    {RULE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {ruleTypeLabel(type)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-[var(--foreground-muted)] mb-1">
                    {paramLabel(newRuleType)}
                  </label>
                  <input
                    type="number"
                    value={newRuleValue}
                    onChange={(e) => setNewRuleValue(e.target.value)}
                    placeholder={paramPlaceholder(newRuleType)}
                    className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                    step="any"
                  />
                </div>
                <Button size="sm" onClick={handleAdd} disabled={isMutating}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {addError && <p className="mt-1 text-xs text-red-500">{addError}</p>}
              <p className="mt-2 text-xs text-[var(--foreground-muted)]">
                {t('sellRuleHint')}
              </p>
            </div>
          ) : (
            /* Presets Tab */
            <div>
              {presetsLoading ? (
                <div className="space-y-2 animate-pulse py-2">
                  <div className="h-16 rounded bg-[var(--border)]" />
                  <div className="h-16 rounded bg-[var(--border)]" />
                </div>
              ) : presets.length === 0 ? (
                <p className="text-center text-sm text-[var(--foreground-muted)] py-4">
                  {t('noSellRulePresets')}
                </p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {presets.map((preset) => {
                    const applied = isPresetApplied(preset.id);
                    const inactive = !preset.is_active;
                    return (
                      <div
                        key={preset.id}
                        className="rounded-lg border border-[var(--border)] px-3 py-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-[var(--foreground)] truncate">
                              {preset.name}
                            </p>
                            {preset.description && (
                              <p className="text-xs text-[var(--foreground-muted)] truncate mt-0.5">
                                {preset.description}
                              </p>
                            )}
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {preset.rules.map((rule, idx) => (
                                <span
                                  key={idx}
                                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${ruleTypeColor(rule.rule_type)}`}
                                >
                                  {ruleTypeLabel(rule.rule_type)}
                                </span>
                              ))}
                              <span className="text-xs text-[var(--foreground-muted)] self-center">
                                {preset.rules.length} {t('sellRulePresetRules')}
                              </span>
                            </div>
                          </div>
                          <div className="ml-3 flex-shrink-0">
                            {inactive ? (
                              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500 dark:bg-gray-800 dark:text-gray-500">
                                {t('sellRulePresetInactive')}
                              </span>
                            ) : applied ? (
                              <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                                {t('sellRulePresetApplied')}
                              </span>
                            ) : (
                              <Button
                                size="sm"
                                onClick={() => handleApplyPreset(preset.id)}
                                disabled={isMutating}
                              >
                                {t('applySellRulePreset')}
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {presetError && <p className="mt-2 text-xs text-red-500">{presetError}</p>}
            </div>
          )}
        </div>

        {/* Footer: Save as Preset */}
        {rules.length > 0 && (
          <div className="border-t border-[var(--border)] px-6 py-3 flex items-center justify-between">
            <Button
              size="sm"
              variant="outline"
              onClick={handleSaveAsPreset}
              disabled={isMutating}
            >
              <Save className="h-3.5 w-3.5 mr-1" />
              {t('saveAsPreset')}
            </Button>
            {savePresetMsg && (
              <span className="text-xs text-[var(--foreground-muted)]">{savePresetMsg}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
