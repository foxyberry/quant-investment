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
  TrendingUp,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import LocaleSwitcher from './LocaleSwitcher';

interface NavItem {
  href: '/' | '/screening' | '/strategy' | '/portfolio' | '/analysis' | '/reports';
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
          fixed top-0 left-0 z-40 h-screen
          bg-[#101622]
          transition-sidebar
          ${isCollapsed ? 'w-[var(--sidebar-collapsed-width)]' : 'w-[var(--sidebar-width)]'}
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
        role="navigation"
        aria-label="Sidebar navigation"
      >
        <div className="flex h-full flex-col">
          {/* Branding */}
          <div className={`px-4 py-5 ${isCollapsed ? 'flex justify-center' : ''}`}>
            <Link href="/" onClick={onClose} className="flex items-center gap-3 group">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white flex-shrink-0 group-hover:bg-blue-500 transition-colors">
                <TrendingUp className="h-5 w-5" />
              </div>
              {!isCollapsed && (
                <div>
                  <span className="text-lg font-bold text-white">Quant</span>
                  <p className="text-[10px] uppercase tracking-widest text-slate-500">Fintech Platform</p>
                </div>
              )}
            </Link>
          </div>

          {/* Navigation items */}
          <nav className="flex-1 overflow-y-auto px-3 py-2">
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
                            ? 'bg-blue-600 text-white'
                            : 'text-slate-400 hover:bg-white/5 hover:text-white'
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

          {/* Bottom section: Locale + Settings + Collapse */}
          <div className="border-t border-white/10 px-3 py-3 space-y-1">
            {/* Locale Switcher */}
            <div className={`flex ${isCollapsed ? 'justify-center' : 'px-1'}`}>
              <LocaleSwitcher variant="sidebar" />
            </div>

            {/* Settings */}
            <Link
              href="/settings"
              onClick={onClose}
              className={`
                flex items-center gap-3 rounded-lg px-3 py-2.5 font-medium transition-colors
                ${
                  isActive('/settings')
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                }
              `}
              aria-current={isActive('/settings') ? 'page' : undefined}
            >
              <Settings className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && <span>{t('settings')}</span>}
            </Link>

            {/* Collapse toggle - Desktop only */}
            <div className="hidden lg:block">
              <button
                type="button"
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-500 hover:bg-white/5 hover:text-slate-300 transition-colors"
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
        </div>
      </aside>
    </>
  );
}
