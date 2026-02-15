'use client';

import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { Globe } from 'lucide-react';
import type { Locale } from '@/i18n/routing';

const localeLabels: Record<Locale, string> = {
  en: 'EN',
  ko: 'KO',
};

export default function LocaleSwitcher() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();

  const nextLocale: Locale = locale === 'en' ? 'ko' : 'en';

  const handleSwitch = () => {
    router.replace(pathname, { locale: nextLocale });
  };

  return (
    <button
      type="button"
      onClick={handleSwitch}
      className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
      aria-label={`Switch to ${nextLocale === 'en' ? 'English' : '한국어'}`}
    >
      <Globe className="h-4 w-4" />
      <span>{localeLabels[locale]}</span>
    </button>
  );
}
