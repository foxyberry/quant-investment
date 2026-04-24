'use client';

import { createContext, useContext, useState, useSyncExternalStore, useCallback, type ReactNode } from 'react';
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

function loadSettings(): UserSettings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<UserSettings>;
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function saveSettings(settings: UserSettings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
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
  const storedSettings = useSyncExternalStore(subscribe, loadSettings, () => DEFAULT_SETTINGS);
  const [overrideSettings, setOverrideSettings] = useState<UserSettings | null>(null);

  // overrideSettings takes precedence (for immediate updates within the same tab)
  const settings = overrideSettings ?? storedSettings;

  const updateBaseCurrency = useCallback((currency: BaseCurrency) => {
    const next = { ...settings, baseCurrency: currency };
    saveSettings(next);
    setOverrideSettings(next);
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
