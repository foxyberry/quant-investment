'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { Globe } from 'lucide-react';
import type { Locale } from '@/i18n/routing';

const localeLabels: Record<Locale, string> = {
  en: 'EN',
  ko: 'KO',
  zh: 'ZH',
};

const localeOrder: Locale[] = ['en', 'ko', 'zh'];
const LOCALE_SYNC_KEY = 'quant-investment:locale-sync';

interface LocaleSwitcherProps {
  variant?: 'default' | 'sidebar';
}

export default function LocaleSwitcher({ variant = 'default' }: LocaleSwitcherProps) {
  const locale = useLocale() as Locale;
  const tNav = useTranslations('nav');
  const router = useRouter();
  const pathname = usePathname();

  const currentIndex = localeOrder.indexOf(locale);
  const nextLocale = localeOrder[(currentIndex + 1) % localeOrder.length];

  const handleSwitch = () => {
    // Set cookie so next-intl middleware remembers the preference on refresh
    document.cookie = `NEXT_LOCALE=${nextLocale}; path=/; max-age=31536000; SameSite=Lax`;
    // Sync across tabs via localStorage
    window.localStorage.setItem(
      LOCALE_SYNC_KEY,
      JSON.stringify({ locale: nextLocale })
    );
    router.replace(pathname, { locale: nextLocale });
  };

  const baseClasses = "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors";
  const variantClasses = variant === 'sidebar'
    ? 'text-slate-400 hover:bg-white/5 hover:text-white'
    : 'text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)]';

  return (
    <button
      type="button"
      onClick={handleSwitch}
      className={`${baseClasses} ${variantClasses}`}
      aria-label={tNav('switchToLocale', { locale: localeLabels[nextLocale] })}
    >
      <Globe className="h-4 w-4" />
      <span>{localeLabels[locale]}</span>
    </button>
  );
}
