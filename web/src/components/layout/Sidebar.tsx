'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Search,
  PieChart,
  BarChart3,
  Workflow,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const navItems: NavItem[] = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/screening', label: 'Screening', icon: Search },
  { href: '/strategy', label: 'Strategy', icon: Workflow },
  { href: '/portfolio', label: 'Portfolio', icon: PieChart },
  { href: '/analysis', label: 'Analysis', icon: BarChart3 },
  { href: '/settings', label: 'Settings', icon: Settings },
];

interface SidebarProps {
  /** Whether sidebar is open on mobile */
  isOpen?: boolean;
  /** Callback when sidebar should close on mobile */
  onClose?: () => void;
}

/**
 * Sidebar navigation component with collapsible functionality
 */
export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();

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
                        <span className="truncate">{item.label}</span>
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
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight className="h-5 w-5" />
              ) : (
                <>
                  <ChevronLeft className="h-5 w-5" />
                  <span>Collapse</span>
                </>
              )}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
