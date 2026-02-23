'use client';

import { useEffect, useRef, useState } from 'react';
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
import { getKiwoomConnectionStatus } from '@/lib/api';
import type { KiwoomConnectionState, KiwoomConnectionStatus } from '@/lib/types';
import { Toast, useToast } from '@/components/ui/Toast';

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

const DEFAULT_KIWOOM_STATUS: KiwoomConnectionStatus = {
  status: 'unavailable',
  is_mock_trading: null,
  user_id: null,
  accounts: [],
  updated_at: null,
};

function maskAccount(account: string): string {
  if (account.length <= 4) return account;
  return `${account.slice(0, 3)}****${account.slice(-2)}`;
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();
  const tNav = useTranslations('nav');
  const tKiwoom = useTranslations('kiwoom');
  const { toast, showToast, hideToast } = useToast();
  const [kiwoomStatus, setKiwoomStatus] = useState<KiwoomConnectionStatus>(DEFAULT_KIWOOM_STATUS);
  const previousStatusRef = useRef<KiwoomConnectionState | null>(null);

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  useEffect(() => {
    let mounted = true;

    const fetchStatus = async () => {
      const next = await getKiwoomConnectionStatus();
      if (!mounted) return;

      if (previousStatusRef.current === 'connected' && next.status === 'disconnected') {
        showToast(tKiwoom('disconnectedToast'), 'error');
      }

      previousStatusRef.current = next.status;
      setKiwoomStatus(next);
    };

    fetchStatus();
    const intervalId = window.setInterval(fetchStatus, 10000);

    return () => {
      mounted = false;
      window.clearInterval(intervalId);
    };
  }, [showToast, tKiwoom]);

  const statusDotClass: Record<KiwoomConnectionState, string> = {
    connected: 'bg-emerald-400',
    disconnected: 'bg-red-400',
    connecting: 'bg-amber-400',
    unavailable: 'bg-slate-500',
  };

  const statusText: Record<KiwoomConnectionState, string> = {
    connected: tKiwoom('connected'),
    disconnected: tKiwoom('disconnected'),
    connecting: tKiwoom('connecting'),
    unavailable: tKiwoom('unavailable'),
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

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
                      {!isCollapsed && <span className="truncate">{tNav(item.labelKey)}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          <div className="border-t border-white/10 px-3 py-3 space-y-2">
            <div
              className={`rounded-lg border border-white/10 bg-white/5 ${
                isCollapsed ? 'px-0 py-2' : 'px-3 py-2.5'
              }`}
            >
              {isCollapsed ? (
                <div className="flex justify-center" aria-label={statusText[kiwoomStatus.status]}>
                  <span className={`h-2.5 w-2.5 rounded-full ${statusDotClass[kiwoomStatus.status]}`} />
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold tracking-wide text-slate-300">
                      {tKiwoom('title')}
                    </span>
                    <span className={`h-2.5 w-2.5 rounded-full ${statusDotClass[kiwoomStatus.status]}`} />
                  </div>
                  <p className="text-xs text-slate-200">{statusText[kiwoomStatus.status]}</p>
                  <span className="inline-block rounded bg-slate-700/70 px-1.5 py-0.5 text-[10px] text-slate-200">
                    {kiwoomStatus.is_mock_trading === true
                      ? tKiwoom('mockTrading')
                      : kiwoomStatus.is_mock_trading === false
                      ? tKiwoom('liveTrading')
                      : tKiwoom('unavailable')}
                  </span>
                  <p className="text-[11px] text-slate-400">
                    {tKiwoom('user')}: {kiwoomStatus.user_id ?? '-'}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {tKiwoom('account')}:{' '}
                    {kiwoomStatus.accounts[0]
                      ? maskAccount(kiwoomStatus.accounts[0])
                      : tKiwoom('noAccount')}
                  </p>
                </div>
              )}
            </div>

            <div className={`flex ${isCollapsed ? 'justify-center' : 'px-1'}`}>
              <LocaleSwitcher variant="sidebar" />
            </div>

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
              {!isCollapsed && <span>{tNav('settings')}</span>}
            </Link>

            <div className="hidden lg:block">
              <button
                type="button"
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-500 hover:bg-white/5 hover:text-slate-300 transition-colors"
                aria-label={isCollapsed ? tNav('expandSidebar') : tNav('collapseSidebar')}
              >
                {isCollapsed ? (
                  <ChevronRight className="h-5 w-5" />
                ) : (
                  <>
                    <ChevronLeft className="h-5 w-5" />
                    <span>{tNav('collapseSidebar')}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </aside>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type as 'error' | 'warning' | 'info' | 'success'}
          onClose={hideToast}
        />
      )}
    </>
  );
}
