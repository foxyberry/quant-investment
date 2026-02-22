'use client';

import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { Globe } from 'lucide-react';
import type { Locale } from '@/i18n/routing';

const localeLabels: Record<Locale, string> = {
  en: 'EN',
  ko: 'KO',
  zh: 'ZH',
};

const localeOrder: Locale[] = ['en', 'ko', 'zh'];

interface LocaleSwitcherProps {
  variant?: 'default' | 'sidebar';
}

export default function LocaleSwitcher({ variant = 'default' }: LocaleSwitcherProps) {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();

  const currentIndex = localeOrder.indexOf(locale);
  const nextLocale = localeOrder[(currentIndex + 1) % localeOrder.length];

  const handleSwitch = () => {
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
      aria-label={`Switch to ${nextLocale}`}
    >
      <Globe className="h-4 w-4" />
      <span>{localeLabels[locale]}</span>
    </button>
  );
}
