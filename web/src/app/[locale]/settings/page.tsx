'use client';

import { useTranslations } from 'next-intl';
import { useLocale } from 'next-intl';
import { Globe, DollarSign } from 'lucide-react';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { BASE_CURRENCIES, CURRENCY_LABELS } from '@/lib/format';
import type { BaseCurrency } from '@/lib/format';
import { useRouter, usePathname } from '@/i18n/navigation';
import { routing } from '@/i18n/routing';

const LOCALE_LABELS: Record<string, string> = {
  en: 'English',
  ko: '한국어',
  zh: '中文',
};
const LOCALE_SYNC_KEY = 'quant-investment:locale-sync';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const { settings, updateBaseCurrency } = useUserSettings();

  const handleLocaleChange = (newLocale: string) => {
    window.localStorage.setItem(
      LOCALE_SYNC_KEY,
      JSON.stringify({ locale: newLocale })
    );
    router.replace(pathname, { locale: newLocale });
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
                    onClick={() => handleLocaleChange(loc)}
                    className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                      locale === loc
                        ? 'bg-blue-600 text-white'
                        : 'bg-[var(--background)] text-[var(--foreground-muted)] hover:text-[var(--foreground)] border border-[var(--border)]'
                    }`}
                  >
                    {LOCALE_LABELS[loc] ?? loc}
                  </button>
                ))}
              </div>
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
    </div>
  );
}
