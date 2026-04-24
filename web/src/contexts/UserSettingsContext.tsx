'use client';

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
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

export function UserSettingsProvider({ children }: { children: ReactNode }) {
  // Always initialize with DEFAULT_SETTINGS so SSR and client initial render match.
  // Sync from localStorage after mount to avoid hydration mismatch.
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const updateBaseCurrency = useCallback((currency: BaseCurrency) => {
    setSettings((prev) => {
      const next = { ...prev, baseCurrency: currency };
      saveSettings(next);
      return next;
    });
  }, []);

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
