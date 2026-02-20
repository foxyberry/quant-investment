'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import {
  LayoutDashboard,
  Search,
  PieChart,
  BarChart3,
  FileText,
  Workflow,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface NavItem {
  href: '/' | '/screening' | '/strategy' | '/portfolio' | '/analysis' | '/reports' | '/settings';
  labelKey: string;
  icon: LucideIcon;
}

const navItems: NavItem[] = [
  { href: '/', labelKey: 'dashboard', icon: LayoutDashboard },
  { href: '/screening', labelKey: 'screening', icon: Search },
  { href: '/strategy', labelKey: 'strategy', icon: Workflow },
  { href: '/portfolio', labelKey: 'portfolio', icon: PieChart },
  { href: '/analysis', labelKey: 'analysis', icon: BarChart3 },
  { href: '/reports', labelKey: 'reports', icon: FileText },
  { href: '/settings', labelKey: 'settings', icon: Settings },
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();
  const t = useTranslations('nav');

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-[var(--header-height)] left-0 z-40 h-[calc(100vh-var(--header-height))]
          border-r border-[var(--border)] bg-[var(--background-secondary)]
          transition-sidebar
          ${isCollapsed ? 'w-[var(--sidebar-collapsed-width)]' : 'w-[var(--sidebar-width)]'}
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
        role="navigation"
        aria-label="Sidebar navigation"
      >
        <div className="flex h-full flex-col">
          {/* Navigation items */}
          <nav className="flex-1 overflow-y-auto p-3">
            <ul className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);

                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onClose}
                      className={`
                        flex items-center gap-3 rounded-lg px-3 py-2.5 font-medium transition-colors
                        ${
                          active
                            ? 'bg-[var(--color-primary)] text-white'
                            : 'text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)]'
                        }
                      `}
                      aria-current={active ? 'page' : undefined}
                    >
                      <Icon className="h-5 w-5 flex-shrink-0" />
                      {!isCollapsed && (
                        <span className="truncate">{t(item.labelKey)}</span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Collapse toggle - Desktop only */}
          <div className="hidden lg:block border-t border-[var(--border)] p-3">
            <button
              type="button"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)] transition-colors"
              aria-label={isCollapsed ? t('expandSidebar') : t('collapseSidebar')}
            >
              {isCollapsed ? (
                <ChevronRight className="h-5 w-5" />
              ) : (
                <>
                  <ChevronLeft className="h-5 w-5" />
                  <span>{t('collapseSidebar')}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
