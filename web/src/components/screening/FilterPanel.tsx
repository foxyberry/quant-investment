'use client';

import { useEffect, useState } from 'react';
import { Play, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui';
import { getPresets, getUniverses } from '@/lib/api';
import type { PresetInfo, UniverseInfo } from '@/lib/types';

interface FilterPanelProps {
  /** Currently selected preset */
  selectedPreset: string;
  /** Currently selected universe */
  selectedUniverse: string;
  /** Whether screening is in progress */
  isLoading: boolean;
  /** Callback when preset changes */
  onPresetChange: (preset: string) => void;
  /** Callback when universe changes */
  onUniverseChange: (universe: string) => void;
  /** Callback when run button is clicked */
  onRun: () => void;
}

/**
 * Filter panel for selecting screening preset and universe
 */
export default function FilterPanel({
  selectedPreset,
  selectedUniverse,
  isLoading,
  onPresetChange,
  onUniverseChange,
  onRun,
}: FilterPanelProps) {
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
        setError('Failed to load presets');
      } finally {
        setLoadingPresets(false);
      }
    };

    const loadUniverses = async () => {
      try {
        setLoadingUniverses(true);
        const data = await getUniverses();
        setUniverses(data);
        if (data.length > 0 && !selectedUniverse) {
          onUniverseChange(data[0].name);
        }
      } catch (err) {
        console.error('Failed to load universes:', err);
        setError('Failed to load universes');
      } finally {
        setLoadingUniverses(false);
      }
    };

    loadPresets();
    loadUniverses();
  }, [onPresetChange, onUniverseChange, selectedPreset, selectedUniverse]);

  const selectedPresetInfo = presets.find((p) => p.name === selectedPreset);
  const canRun = selectedPreset && selectedUniverse && !isLoading;

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-6">
      <h2 className="mb-4 text-lg font-semibold text-[var(--foreground)]">
        Screening Filters
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
            Preset
          </label>
          <select
            id="preset-select"
            value={selectedPreset}
            onChange={(e) => onPresetChange(e.target.value)}
            disabled={loadingPresets || isLoading}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] focus:border-[var(--color-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-opacity-20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loadingPresets ? (
              <option value="">Loading presets...</option>
            ) : presets.length === 0 ? (
              <option value="">No presets available</option>
            ) : (
              presets.map((preset) => (
                <option key={preset.name} value={preset.name}>
                  {preset.name}
                </option>
              ))
            )}
          </select>
          {selectedPresetInfo && (
            <p className="mt-1.5 text-sm text-[var(--foreground-muted)]">
              {selectedPresetInfo.description}
            </p>
          )}
        </div>

        {/* Universe Selector */}
        <div>
          <label
            htmlFor="universe-select"
            className="mb-1.5 block text-sm font-medium text-[var(--foreground)]"
          >
            Universe
          </label>
          <select
            id="universe-select"
            value={selectedUniverse}
            onChange={(e) => onUniverseChange(e.target.value)}
            disabled={loadingUniverses || isLoading}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] focus:border-[var(--color-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-opacity-20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loadingUniverses ? (
              <option value="">Loading universes...</option>
            ) : universes.length === 0 ? (
              <option value="">No universes available</option>
            ) : (
              universes.map((universe) => (
                <option key={universe.name} value={universe.name}>
                  {universe.name} ({universe.stock_count.toLocaleString()} stocks)
                </option>
              ))
            )}
          </select>
        </div>

        {/* Conditions Preview */}
        {selectedPresetInfo && selectedPresetInfo.conditions.length > 0 && (
          <div>
            <p className="mb-1.5 text-sm font-medium text-[var(--foreground)]">
              Conditions
            </p>
            <ul className="space-y-1 text-sm text-[var(--foreground-muted)]">
              {selectedPresetInfo.conditions.map((condition, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-[var(--color-primary)]">-</span>
                  <span>{condition}</span>
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
              Screening...
            </>
          ) : (
            <>
              <Play className="mr-2 h-5 w-5" />
              Run Screening
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
