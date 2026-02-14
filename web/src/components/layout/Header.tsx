'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Menu, X, TrendingUp } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import LocaleSwitcher from './LocaleSwitcher';

const navKeys = ['dashboard', 'screening', 'portfolio', 'analysis'] as const;
const navHrefs = ['/', '/screening', '/portfolio', '/analysis'] as const;

interface HeaderProps {
  onMenuClick?: () => void;
  isSidebarOpen?: boolean;
}

export default function Header({ onMenuClick, isSidebarOpen }: HeaderProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const t = useTranslations('nav');

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-[var(--header-height)] border-b border-[var(--border)] bg-[var(--background-secondary)]">
      <div className="flex h-full items-center justify-between px-4 lg:px-6">
        {/* Left section: Menu button + Logo */}
        <div className="flex items-center gap-4">
          <button
            type="button"
            className="lg:hidden p-2 rounded-lg text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            onClick={onMenuClick}
            aria-label={isSidebarOpen ? t('closeSidebar') : t('openSidebar')}
            aria-expanded={isSidebarOpen}
          >
            {isSidebarOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </button>

          <Link href="/" className="flex items-center gap-2 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--color-primary)] text-white group-hover:bg-[var(--color-primary-light)] transition-colors">
              <TrendingUp className="h-5 w-5" />
            </div>
            <span className="hidden sm:block text-lg font-bold text-[var(--foreground)]">
              Quant Investment
            </span>
          </Link>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-1" role="navigation" aria-label="Main navigation">
          {navKeys.map((key, i) => (
            <Link
              key={key}
              href={navHrefs[i]}
              className="px-4 py-2 text-sm font-medium text-[var(--foreground-muted)] hover:text-[var(--foreground)] hover:bg-[var(--border)] rounded-lg transition-colors"
            >
              {t(key)}
            </Link>
          ))}
        </nav>

        {/* Right section: Locale switcher + Mobile nav toggle */}
        <div className="flex items-center gap-2">
          <LocaleSwitcher />

          <button
            type="button"
            className="md:hidden p-2 rounded-lg text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label={isMobileMenuOpen ? t('closeNavMenu') : t('openNavMenu')}
            aria-expanded={isMobileMenuOpen}
          >
            {isMobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Dropdown */}
      {isMobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 border-b border-[var(--border)] bg-[var(--background-secondary)] shadow-lg">
          <nav className="flex flex-col p-2" role="navigation" aria-label="Mobile navigation">
            {navKeys.map((key, i) => (
              <Link
                key={key}
                href={navHrefs[i]}
                className="px-4 py-3 text-sm font-medium text-[var(--foreground-muted)] hover:text-[var(--foreground)] hover:bg-[var(--border)] rounded-lg transition-colors"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                {t(key)}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
