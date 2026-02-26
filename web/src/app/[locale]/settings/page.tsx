'use client';

import { useTranslations } from 'next-intl';
import { useLocale } from 'next-intl';
import { useEffect, useState } from 'react';
import { Globe, DollarSign, PlugZap, RefreshCw, Link2Off } from 'lucide-react';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { BASE_CURRENCIES, CURRENCY_LABELS } from '@/lib/format';
import type { BaseCurrency } from '@/lib/format';
import { useRouter, usePathname } from '@/i18n/navigation';
import { routing } from '@/i18n/routing';
import { getBrokerConnectionStatus, getSettingsBrokerStatuses } from '@/lib/api';
import type { BrokerConnectionStatus, BrokerConnectionState } from '@/lib/types';

const LOCALE_LABELS: Record<string, string> = {
  en: 'English',
  ko: '한국어',
  zh: '中文',
};
const LOCALE_SYNC_KEY = 'quant-investment:locale-sync';

export default function SettingsPage() {
  const tCommon = useTranslations('common');
  const t = useTranslations('settings');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const { settings, updateBaseCurrency } = useUserSettings();
  const [selectedLocale, setSelectedLocale] = useState(locale);
  const [brokers, setBrokers] = useState<BrokerConnectionStatus[]>([]);
  const [loadingBrokers, setLoadingBrokers] = useState(true);
  const [brokerError, setBrokerError] = useState<string | null>(null);
  const [refreshingBroker, setRefreshingBroker] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);

  const statusTextKey: Record<BrokerConnectionState, string> = {
    connected: 'connected',
    disconnected: 'disconnected',
    connecting: 'connecting',
    unavailable: 'unavailable',
  };
  const statusDotClass: Record<BrokerConnectionState, string> = {
    connected: 'bg-green-500',
    disconnected: 'bg-slate-400',
    connecting: 'bg-amber-500 animate-pulse',
    unavailable: 'bg-red-500',
  };

  useEffect(() => {
    setSelectedLocale(locale);
  }, [locale]);

  useEffect(() => {
    const load = async () => {
      setLoadingBrokers(true);
      setBrokerError(null);
      try {
        const result = await getSettingsBrokerStatuses();
        setBrokers(result);
      } catch (e) {
        setBrokerError(e instanceof Error ? e.message : 'Failed to load broker status');
      } finally {
        setLoadingBrokers(false);
      }
    };
    load();
  }, []);

  const handleLocaleSave = () => {
    if (selectedLocale === locale) return;
    // Set cookie so next-intl middleware remembers the preference on refresh
    document.cookie = `NEXT_LOCALE=${selectedLocale}; path=/; max-age=31536000; SameSite=Lax`;
    // Sync across tabs via localStorage
    window.localStorage.setItem(
      LOCALE_SYNC_KEY,
      JSON.stringify({ locale: selectedLocale })
    );
    router.replace(pathname, { locale: selectedLocale });
  };

  const maskAccount = (value: string): string => {
    if (value.length <= 4) return value;
    return `${value.slice(0, 3)}****${value.slice(-2)}`;
  };

  const formatUpdatedAt = (value: string | null): string => {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '-';
    return new Intl.DateTimeFormat(locale, {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    setBrokerError(null);
    try {
      const result = await getSettingsBrokerStatuses();
      setBrokers(result);
    } catch (e) {
      setBrokerError(e instanceof Error ? e.message : 'Failed to sync broker status');
    } finally {
      setSyncingAll(false);
    }
  };

  const handleTestBroker = async (broker: string) => {
    setRefreshingBroker(broker);
    setBrokerError(null);
    try {
      const status = await getBrokerConnectionStatus(broker);
      setBrokers((prev) =>
        prev.map((item) => (item.broker === broker ? status : item))
      );
    } catch (e) {
      setBrokerError(e instanceof Error ? e.message : 'Failed to test broker connection');
    } finally {
      setRefreshingBroker(null);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">{t('title')}</h1>
        <p className="mt-1 text-[var(--foreground-muted)]">{t('subtitle')}</p>
      </div>

      {/* General Section */}
      <section className="space-y-6">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">{t('general')}</h2>

        {/* Language */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-blue-50 p-3 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400">
              <Globe className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-[var(--foreground)]">{t('language')}</h3>
              <p className="mt-1 text-sm text-[var(--foreground-muted)]">{t('languageDesc')}</p>
              <div className="mt-4 flex gap-2 flex-wrap">
                {routing.locales.map((loc) => (
                  <button
                    key={loc}
                    type="button"
                    onClick={() => setSelectedLocale(loc)}
                    className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                      selectedLocale === loc
                        ? 'bg-blue-600 text-white'
                        : 'bg-[var(--background)] text-[var(--foreground-muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
                    }`}
                  >
                    {LOCALE_LABELS[loc] ?? loc}
                  </button>
                ))}
              </div>
              {selectedLocale !== locale && (
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={handleLocaleSave}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                  >
                    {tCommon('save')}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Base Currency */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-amber-50 p-3 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400">
              <DollarSign className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-[var(--foreground)]">{t('baseCurrency')}</h3>
              <p className="mt-1 text-sm text-[var(--foreground-muted)]">{t('baseCurrencyDesc')}</p>
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
                {BASE_CURRENCIES.map((currency) => (
                  <button
                    key={currency}
                    type="button"
                    onClick={() => updateBaseCurrency(currency as BaseCurrency)}
                    className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      settings.baseCurrency === currency
                        ? 'bg-amber-600 text-white'
                        : 'bg-[var(--background)] text-[var(--foreground-muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
                    }`}
                  >
                    {currency}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-[var(--foreground-muted)]">
                {CURRENCY_LABELS[settings.baseCurrency]}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">{t('brokerConnections')}</h2>
          <button
            type="button"
            onClick={handleSyncAll}
            disabled={syncingAll || loadingBrokers}
            className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background)] disabled:opacity-60"
          >
            <span className="inline-flex items-center gap-2">
              <RefreshCw className={`h-4 w-4 ${syncingAll ? 'animate-spin' : ''}`} />
              {t('sync')}
            </span>
          </button>
        </div>

        {brokerError && (
          <div className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
            {brokerError}
          </div>
        )}

        <div className="space-y-3">
          {loadingBrokers ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-4 text-sm text-[var(--foreground-muted)]">
              {t('loading')}
            </div>
          ) : (
            brokers.map((broker) => (
              <div
                key={broker.broker}
                className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-4"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <PlugZap className="h-4 w-4 text-[var(--foreground-muted)]" />
                      <span className="font-medium text-[var(--foreground)]">{broker.broker.toUpperCase()}</span>
                      <span className={`h-2.5 w-2.5 rounded-full ${statusDotClass[broker.status]}`} />
                      <span className="text-sm text-[var(--foreground-muted)]">
                        {t(statusTextKey[broker.status])}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--foreground-muted)]">
                      {t('accountsCount', { count: broker.accounts.length })}
                      {broker.accounts[0] ? ` · ${t('primaryAccount')}: ${maskAccount(broker.accounts[0])}` : ''}
                    </p>
                    <p className="text-xs text-[var(--foreground-muted)]">
                      {t('lastChecked')}: {formatUpdatedAt(broker.updated_at)}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleTestBroker(broker.broker)}
                      disabled={refreshingBroker === broker.broker}
                      className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--background-secondary)] disabled:opacity-60"
                    >
                      <span className="inline-flex items-center gap-2">
                        <RefreshCw className={`h-4 w-4 ${refreshingBroker === broker.broker ? 'animate-spin' : ''}`} />
                        {t('testConnection')}
                      </span>
                    </button>
                    <button
                      type="button"
                      disabled
                      title={t('disconnectPhaseLater')}
                      className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm font-medium text-[var(--foreground-muted)] opacity-70"
                    >
                      <span className="inline-flex items-center gap-2">
                        <Link2Off className="h-4 w-4" />
                        {t('disconnect')}
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
