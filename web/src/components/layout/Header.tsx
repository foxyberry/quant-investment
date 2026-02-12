'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, X, TrendingUp } from 'lucide-react';

interface NavLink {
  href: string;
  label: string;
}

const navLinks: NavLink[] = [
  { href: '/', label: 'Dashboard' },
  { href: '/screening', label: 'Screening' },
  { href: '/portfolio', label: 'Portfolio' },
  { href: '/analysis', label: 'Analysis' },
];

interface HeaderProps {
  /** Toggle sidebar visibility on mobile */
  onMenuClick?: () => void;
  /** Whether sidebar is currently open on mobile */
  isSidebarOpen?: boolean;
}

/**
 * Header component with logo, navigation, and mobile menu
 */
export default function Header({ onMenuClick, isSidebarOpen }: HeaderProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-[var(--header-height)] border-b border-[var(--border)] bg-[var(--background-secondary)]">
      <div className="flex h-full items-center justify-between px-4 lg:px-6">
        {/* Left section: Menu button + Logo */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button for sidebar */}
          <button
            type="button"
            className="lg:hidden p-2 rounded-lg text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            onClick={onMenuClick}
            aria-label={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            aria-expanded={isSidebarOpen}
          >
            {isSidebarOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </button>

          {/* Logo */}
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
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="px-4 py-2 text-sm font-medium text-[var(--foreground-muted)] hover:text-[var(--foreground)] hover:bg-[var(--border)] rounded-lg transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right section: User menu / Mobile nav toggle */}
        <div className="flex items-center gap-2">
          {/* Mobile navigation toggle */}
          <button
            type="button"
            className="md:hidden p-2 rounded-lg text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
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
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="px-4 py-3 text-sm font-medium text-[var(--foreground-muted)] hover:text-[var(--foreground)] hover:bg-[var(--border)] rounded-lg transition-colors"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
