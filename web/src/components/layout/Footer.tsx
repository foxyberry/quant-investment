'use client';

import { useTranslations } from 'next-intl';

export default function Footer() {
  const currentYear = new Date().getFullYear();
  const version = process.env.NEXT_PUBLIC_APP_VERSION || '0.1.0';
  const t = useTranslations('common');

  return (
    <footer className="border-t border-[var(--border)] bg-[var(--background-secondary)] py-4 px-6">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-[var(--foreground-muted)]">
        <p>{t('copyright', { year: currentYear })}</p>
        <p>{t('version', { version })}</p>
      </div>
    </footer>
  );
}
