'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Link2, Plus, Trash2, X } from 'lucide-react';
import { Button } from '@/components/ui';
import {
  getBuyRules,
  createBuyRule,
  updateBuyRule,
  deleteBuyRule,
  getBuyRuleTemplates,
  createRuleFromTemplate,
} from '@/lib/api';
import type { WatchlistItem, BuyRule, BuyRuleCreate, BuyRuleTemplate } from '@/lib/types';

type Tab = 'manual' | 'templates';

interface BuyRuleModalProps {
  item: WatchlistItem;
  onClose: () => void;
  onUpdate: () => void;
}

export default function BuyRuleModal({ item, onClose, onUpdate }: BuyRuleModalProps) {
  const t = useTranslations('watchlist');
  const [rules, setRules] = useState<BuyRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('manual');

  // Templates
  const [templates, setTemplates] = useState<BuyRuleTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [templatesError, setTemplatesError] = useState(false);
  const [linkingId, setLinkingId] = useState<number | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);

  // New rule form
  const [newRuleType, setNewRuleType] = useState<'target_price' | 'rsi_oversold'>('target_price');
  const [newRuleValue, setNewRuleValue] = useState('');
  const [addError, setAddError] = useState<string | null>(null);

  const fetchRules = async () => {
    try {
      const data = await getBuyRules(item.id);
      setRules(data);
    } catch {
      // Fail silently
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    setTemplatesLoading(true);
    setTemplatesError(false);
    try {
      const data = await getBuyRuleTemplates();
      setTemplates(data);
    } catch {
      setTemplatesError(true);
    } finally {
      setTemplatesLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id]);

  useEffect(() => {
    if (activeTab === 'templates' && templates.length === 0 && !templatesLoading && !templatesError) {
      fetchTemplates();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const linkedTemplateIds = new Set(
    rules.filter((r) => r.template_id != null).map((r) => r.template_id as number)
  );

  const handleAdd = async () => {
    const val = parseFloat(newRuleValue);
    if (isNaN(val) || val <= 0) {
      setAddError(t('invalidValue'));
      return;
    }

    setAddError(null);
    const data: BuyRuleCreate = {
      rule_type: newRuleType,
      params: newRuleType === 'target_price' ? { price: val } : { rsi: val },
    };

    try {
      await createBuyRule(item.id, data);
      setNewRuleValue('');
      fetchRules();
      onUpdate();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : t('addRuleFailed'));
    }
  };

  const handleLinkTemplate = async (templateId: number) => {
    setLinkingId(templateId);
    setLinkError(null);
    try {
      await createRuleFromTemplate(item.id, templateId);
      await fetchRules();
      onUpdate();
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : t('linkFailed'));
    } finally {
      setLinkingId(null);
    }
  };

  const handleToggle = async (rule: BuyRule) => {
    try {
      await updateBuyRule(rule.id, { is_active: !rule.is_active });
      fetchRules();
      onUpdate();
    } catch {
      // Fail silently
    }
  };

  const handleDelete = async (ruleId: number) => {
    try {
      await deleteBuyRule(ruleId);
      fetchRules();
      onUpdate();
    } catch {
      // Fail silently
    }
  };

  const ruleTypeLabel = (type: string) => {
    if (type === 'target_price') return t('targetPriceRule');
    if (type === 'rsi_oversold') return t('rsiOversoldRule');
    return type;
  };

  const ruleTypeColor = (type: string) => {
    if (type === 'target_price') return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    if (type === 'rsi_oversold') return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
  };

  const formatRuleValue = (rule: BuyRule) => {
    if (rule.rule_type === 'target_price') {
      const price = rule.params?.price;
      return price != null ? `${Number(price).toLocaleString()}` : '--';
    }
    if (rule.rule_type === 'rsi_oversold') {
      const rsi = rule.params?.rsi;
      return rsi != null ? `RSI ≤ ${rsi}` : '--';
    }
    return '--';
  };

  const formatTemplateValue = (tmpl: BuyRuleTemplate) => {
    if (tmpl.rule_type === 'target_price') {
      const price = tmpl.params?.price;
      return price != null ? `${Number(price).toLocaleString()}` : '--';
    }
    if (tmpl.rule_type === 'rsi_oversold') {
      const rsi = tmpl.params?.rsi;
      return rsi != null ? `RSI ≤ ${rsi}` : '--';
    }
    return '--';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="mx-4 w-full max-w-lg rounded-xl bg-[var(--background-secondary)] shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-[var(--foreground)]">
              {t('buyRules')} - {item.ticker}
            </h2>
            {item.name && (
              <p className="text-sm text-[var(--foreground-muted)]">{item.name}</p>
            )}
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
              {t('noBuyRules')}
            </p>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ruleTypeColor(rule.rule_type)}`}>
                      {ruleTypeLabel(rule.rule_type)}
                    </span>
                    <span className="text-sm font-mono text-[var(--foreground)]">
                      {formatRuleValue(rule)}
                    </span>
                    {rule.template_id != null && (
                      <Link2 className="h-3 w-3 text-[var(--foreground-muted)]" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleToggle(rule)}
                      className={`rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${
                        rule.is_active
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500'
                      }`}
                    >
                      {rule.is_active ? t('active') : t('inactive')}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(rule.id)}
                      className="rounded-md p-1 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Tab bar */}
        <div className="flex border-t border-b border-[var(--border)]">
          <button
            type="button"
            onClick={() => setActiveTab('manual')}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === 'manual'
                ? 'text-[var(--color-primary)] border-b-2 border-[var(--color-primary)]'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {t('manualInput')}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('templates')}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === 'templates'
                ? 'text-[var(--color-primary)] border-b-2 border-[var(--color-primary)]'
                : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {t('savedTemplates')}
          </button>
        </div>

        {/* Tab content */}
        <div className="px-6 py-4">
          {activeTab === 'manual' ? (
            /* Manual Input */
            <div>
              <p className="text-sm font-medium text-[var(--foreground)] mb-2">{t('addBuyRule')}</p>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <label className="block text-xs text-[var(--foreground-muted)] mb-1">{t('ruleType')}</label>
                  <select
                    value={newRuleType}
                    onChange={(e) => setNewRuleType(e.target.value as 'target_price' | 'rsi_oversold')}
                    className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                  >
                    <option value="target_price">{t('targetPriceRule')}</option>
                    <option value="rsi_oversold">{t('rsiOversoldRule')}</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-[var(--foreground-muted)] mb-1">
                    {newRuleType === 'target_price' ? t('price') : t('rsiThreshold')}
                  </label>
                  <input
                    type="number"
                    value={newRuleValue}
                    onChange={(e) => setNewRuleValue(e.target.value)}
                    placeholder={newRuleType === 'target_price' ? '50000' : '30'}
                    className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
                    step="any"
                    min="0"
                  />
                </div>
                <Button size="sm" onClick={handleAdd}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {addError && <p className="mt-1 text-xs text-red-500">{addError}</p>}
            </div>
          ) : (
            /* Templates Tab */
            <div>
              {templatesLoading ? (
                <div className="space-y-2 animate-pulse">
                  <div className="h-10 rounded bg-[var(--border)]" />
                  <div className="h-10 rounded bg-[var(--border)]" />
                </div>
              ) : templatesError ? (
                <div className="flex flex-col items-center gap-2 py-4">
                  <p className="text-sm text-red-500">{t('loadFailed')}</p>
                  <button
                    type="button"
                    onClick={fetchTemplates}
                    className="text-xs text-[var(--color-primary)] hover:underline"
                  >
                    {t('retry') ?? 'Retry'}
                  </button>
                </div>
              ) : templates.length === 0 ? (
                <p className="text-center text-sm text-[var(--foreground-muted)] py-4">
                  {t('noTemplates')}
                </p>
              ) : (
                <div className="space-y-2">
                  {templates.map((tmpl) => {
                    const isLinked = linkedTemplateIds.has(tmpl.id);
                    const isInactive = !tmpl.is_active;
                    const isLinking = linkingId === tmpl.id;
                    const disabled = isLinked || isInactive || isLinking;

                    return (
                      <div
                        key={tmpl.id}
                        className={`flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2 ${
                          disabled ? 'opacity-60' : ''
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${ruleTypeColor(tmpl.rule_type)}`}>
                              {ruleTypeLabel(tmpl.rule_type)}
                            </span>
                            <span className="text-sm font-medium text-[var(--foreground)] truncate">
                              {tmpl.name}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs font-mono text-[var(--foreground-muted)]">
                              {formatTemplateValue(tmpl)}
                            </span>
                            {tmpl.description && (
                              <span className="text-xs text-[var(--foreground-muted)] truncate">
                                · {tmpl.description}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="shrink-0 ml-2">
                          {isLinked ? (
                            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500 dark:bg-gray-800 dark:text-gray-500">
                              {t('alreadyLinked')}
                            </span>
                          ) : isInactive ? (
                            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500 dark:bg-gray-800 dark:text-gray-500">
                              {t('templateInactive')}
                            </span>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => handleLinkTemplate(tmpl.id)}
                              disabled={isLinking}
                            >
                              <Link2 className="h-3.5 w-3.5 mr-1" />
                              {t('linkTemplate')}
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {linkError && <p className="mt-1 text-xs text-red-500">{linkError}</p>}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
