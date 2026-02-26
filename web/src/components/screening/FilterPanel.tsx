'use client';

import { useEffect, useMemo, useState } from 'react';
import { Play, AlertCircle, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui';
import { getPresets, getUniverses } from '@/lib/api';
import type { PresetInfo, UniverseInfo } from '@/lib/types';
import { SAMPLE_STRATEGY_PRESETS } from '@/lib/strategy/sampleStrategies';
import UniverseCheckboxGroup from './UniverseCheckboxGroup';
import DateSelector from './DateSelector';

interface FilterPanelProps {
  selectedPreset: string;
  selectedUniverses: string[];
  referenceDate: string | null;
  isLoading: boolean;
  onPresetChange: (preset: string) => void;
  onUniverseChange: (universes: string[]) => void;
  onReferenceDateChange: (date: string | null) => void;
  onRun: () => void;
  onGraphChange?: (graph: Record<string, unknown> | null) => void;
}

export default function FilterPanel({
  selectedPreset,
  selectedUniverses,
  referenceDate,
  isLoading,
  onPresetChange,
  onUniverseChange,
  onReferenceDateChange,
  onRun,
  onGraphChange,
}: FilterPanelProps) {
  const t = useTranslations('screening');
  const tConditions = useTranslations('conditions');
  const [presets, setPresets] = useState<PresetInfo[]>([]);
  const [universes, setUniverses] = useState<UniverseInfo[]>([]);
  const [loadingPresets, setLoadingPresets] = useState(true);
  const [loadingUniverses, setLoadingUniverses] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPresets = async () => {
      try {
        setLoadingPresets(true);
        const data = await getPresets();
        setPresets(data);
        if (data.length > 0 && !selectedPreset) {
          onPresetChange(data[0].name);
        }
      } catch (err) {
        console.error('Failed to load presets:', err);
        setError(t('failedToLoadPresets'));
      } finally {
        setLoadingPresets(false);
      }
    };

    const loadUniverses = async () => {
      try {
        setLoadingUniverses(true);
        const data = await getUniverses();
        setUniverses(data);
      } catch (err) {
        console.error('Failed to load universes:', err);
        setError(t('failedToLoadUniverses'));
      } finally {
        setLoadingUniverses(false);
      }
    };

    loadPresets();
    loadUniverses();
  }, [onPresetChange, selectedPreset, t]);

  const { staticPresets, customPresets, samplePresets } = useMemo(() => {
    const staticGroup = presets.filter((p) => p.source === 'static');
    const customGroup = presets.filter((p) => p.source === 'custom');

    // Convert SAMPLE_STRATEGY_PRESETS to PresetInfo format
    const sampleGroup: PresetInfo[] = SAMPLE_STRATEGY_PRESETS.map((s) => ({
      name: `sample:${s.key}`,
      description: s.description,
      conditions: s.graph.nodes
        .filter((n) => n.data.node_type === 'condition' && n.data.condition_type)
        .map((n) => n.data.condition_type!),
      source: 'sample' as const,
    }));

    return { staticPresets: staticGroup, customPresets: customGroup, samplePresets: sampleGroup };
  }, [presets]);

  const stockCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const u of universes) {
      counts[u.name] = u.stock_count;
    }
    return counts;
  }, [universes]);

  const selectedPresetInfo = presets.find((p) => p.name === selectedPreset)
    || samplePresets.find((p) => p.name === selectedPreset);
  const canRun = selectedPreset && selectedUniverses.length > 0 && !isLoading;

  const toTitleCaseFromKey = (value: string) =>
    value
      .replace(/^screening\.presetNames\./, '')
      .replace(/^conditions\./, '')
      .replace(/^custom:/, '')
      .replace(/_/g, ' ')
      .replace(/\./g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const presetLabel = (preset: PresetInfo): string => {
    const i18nKey = `presetNames.${preset.name}`;
    if (t.has(i18nKey)) return t(i18nKey as never);
    if (preset.source === 'custom') return preset.description || toTitleCaseFromKey(preset.name);
    if (preset.source === 'sample') return preset.description || toTitleCaseFromKey(preset.name);
    return toTitleCaseFromKey(preset.name);
  };

  const conditionLabel = (condition: string): string => {
    const i18nKey = `${condition}.label`;
    if (tConditions.has(i18nKey)) return tConditions(i18nKey as never);
    return toTitleCaseFromKey(condition);
  };

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-6">
      <h2 className="mb-4 text-lg font-semibold text-[var(--foreground)]">
        {t('filters')}
      </h2>

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="space-y-4">
        {/* Preset Selector */}
        <div>
          <label
            htmlFor="preset-select"
            className="mb-1.5 block text-sm font-medium text-[var(--foreground)]"
          >
            {t('preset')}
          </label>
          <select
            id="preset-select"
            value={selectedPreset}
            onChange={(e) => {
              const value = e.target.value;
              onPresetChange(value);
              if (value.startsWith('sample:')) {
                const sampleKey = value.slice('sample:'.length);
                const sample = SAMPLE_STRATEGY_PRESETS.find((s) => s.key === sampleKey);
                onGraphChange?.(sample ? (sample.graph as unknown as Record<string, unknown>) : null);
              } else {
                onGraphChange?.(null);
              }
            }}
            disabled={loadingPresets || isLoading}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] focus:border-[var(--color-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-opacity-20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loadingPresets ? (
              <option value="">{t('loadingPresets')}</option>
            ) : presets.length === 0 ? (
              <option value="">{t('noPresets')}</option>
            ) : (
              <>
                {staticPresets.length > 0 && (
                  <optgroup label={t('builtInPresets')}>
                    {staticPresets.map((preset) => (
                      <option key={preset.name} value={preset.name}>
                        {presetLabel(preset)}
                      </option>
                    ))}
                  </optgroup>
                )}
                {samplePresets.length > 0 && (
                  <optgroup label={t('sampleStrategies')}>
                    {samplePresets.map((preset) => (
                      <option key={preset.name} value={preset.name}>
                        {presetLabel(preset)}
                      </option>
                    ))}
                  </optgroup>
                )}
                {customPresets.length > 0 && (
                  <optgroup label={t('myStrategies')}>
                    {customPresets.map((preset) => (
                      <option key={preset.name} value={preset.name}>
                        {presetLabel(preset)}
                      </option>
                    ))}
                  </optgroup>
                )}
              </>
            )}
          </select>
          {selectedPresetInfo && (
            <p className="mt-1.5 text-sm text-[var(--foreground-muted)]">
              {selectedPresetInfo.description}
            </p>
          )}
        </div>

        {/* Universe Multi-Select */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[var(--foreground)]">
            {t('universe')}
          </label>
          {loadingUniverses ? (
            <p className="text-sm text-[var(--foreground-muted)]">{t('loadingUniverses')}</p>
          ) : (
            <UniverseCheckboxGroup
              selectedUniverses={selectedUniverses}
              onChange={onUniverseChange}
              stockCounts={stockCounts}
              disabled={isLoading}
            />
          )}
        </div>

        {/* Reference Date Selector */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[var(--foreground)]">
            {t('referenceDate')}
          </label>
          <DateSelector
            value={referenceDate}
            onChange={onReferenceDateChange}
            disabled={isLoading}
          />
        </div>

        {/* Conditions Preview */}
        {selectedPresetInfo && selectedPresetInfo.conditions.length > 0 && (
          <div>
            <p className="mb-1.5 text-sm font-medium text-[var(--foreground)]">
              {t('conditions')}
            </p>
            <ul className="space-y-1 text-sm text-[var(--foreground-muted)]">
              {selectedPresetInfo.conditions.map((condition, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-[var(--color-primary)]">-</span>
                  <span>{conditionLabel(condition)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Run Button */}
        <Button
          onClick={onRun}
          disabled={!canRun}
          isLoading={isLoading}
          fullWidth
          size="lg"
        >
          {isLoading ? (
            <>
              <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
              {t('screening')}
            </>
          ) : (
            <>
              <Play className="mr-2 h-5 w-5" />
              {t('runScreening')}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
