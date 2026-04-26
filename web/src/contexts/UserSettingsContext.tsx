'use client';

import { createContext, useContext, useSyncExternalStore, useCallback, type ReactNode } from 'react';
import type { BaseCurrency } from '@/lib/format';

interface UserSettings {
  baseCurrency: BaseCurrency;
}

interface UserSettingsContextValue {
  settings: UserSettings;
  updateBaseCurrency: (currency: BaseCurrency) => void;
}

const STORAGE_KEY = 'quant-user-settings';

const DEFAULT_SETTINGS: UserSettings = {
  baseCurrency: 'USD',
};

const UserSettingsContext = createContext<UserSettingsContextValue | null>(null);

// Module-level cache so getSnapshot returns a stable reference
// (useSyncExternalStore requires the same object when data hasn't changed)
let _cachedRaw: string | null | undefined = undefined;
let _cachedSettings: UserSettings = DEFAULT_SETTINGS;

function getSnapshot(): UserSettings {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === _cachedRaw) return _cachedSettings;
  _cachedRaw = raw;
  try {
    const parsed = raw ? (JSON.parse(raw) as Partial<UserSettings>) : {};
    _cachedSettings = { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    _cachedSettings = DEFAULT_SETTINGS;
  }
  return _cachedSettings;
}

function saveSettings(settings: UserSettings) {
  try {
    const raw = JSON.stringify(settings);
    localStorage.setItem(STORAGE_KEY, raw);
    // Invalidate cache so getSnapshot picks up the new value
    _cachedRaw = undefined;
  } catch {
    // localStorage may be unavailable (SSR, private browsing quota)
  }
}

// useSyncExternalStore: SSR renders DEFAULT_SETTINGS, client reads localStorage.
// No hydration mismatch, no setState-in-effect.
function subscribe(cb: () => void) {
  window.addEventListener('storage', cb);
  return () => window.removeEventListener('storage', cb);
}

export function UserSettingsProvider({ children }: { children: ReactNode }) {
  const settings = useSyncExternalStore(subscribe, getSnapshot, () => DEFAULT_SETTINGS);

  const updateBaseCurrency = useCallback((currency: BaseCurrency) => {
    saveSettings({ ...settings, baseCurrency: currency });
  }, [settings]);

  return (
    <UserSettingsContext.Provider value={{ settings, updateBaseCurrency }}>
      {children}
    </UserSettingsContext.Provider>
  );
}

export function useUserSettings(): UserSettingsContextValue {
  const ctx = useContext(UserSettingsContext);
  if (!ctx) {
    throw new Error('useUserSettings must be used within a UserSettingsProvider');
  }
  return ctx;
}
