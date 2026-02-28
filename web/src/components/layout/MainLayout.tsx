'use client';

import { useState, ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Menu, X } from 'lucide-react';
import Sidebar from './Sidebar';
import Footer from './Footer';
import LocaleSwitcher from './LocaleSwitcher';

interface MainLayoutProps {
  children: ReactNode;
}

/**
 * Main layout wrapper that combines Sidebar and Footer
 * Handles mobile sidebar state
 * When popup=true query param is present, renders content only (no navigation)
 */
export default function MainLayout({ children }: MainLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const searchParams = useSearchParams();
  const isPopup = searchParams.get('popup') === 'true';
  const t = useTranslations('nav');

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setIsSidebarOpen(false);

  if (isPopup) {
    return <main className="min-h-screen p-4">{children}</main>;
  }

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <Sidebar isOpen={isSidebarOpen} onClose={closeSidebar} />

      {/* Floating mobile header bar */}
      <div className="fixed top-4 left-4 right-4 z-50 lg:hidden flex items-center justify-between">
        <button
          type="button"
          className="p-2 rounded-lg bg-[#101622] text-white shadow-lg hover:bg-[#1a2435] transition-colors"
          onClick={toggleSidebar}
          aria-label={isSidebarOpen ? t('closeSidebar') : t('openSidebar')}
          aria-expanded={isSidebarOpen}
        >
          {isSidebarOpen ? (
            <X className="h-5 w-5" />
          ) : (
            <Menu className="h-5 w-5" />
          )}
        </button>
        <div className="rounded-lg bg-[#101622] shadow-lg">
          <LocaleSwitcher variant="sidebar" />
        </div>
      </div>

      {/* Main content area */}
      <div className="lg:ml-[var(--sidebar-width)] min-h-screen flex flex-col transition-sidebar">
        <main className="flex-1 p-4 lg:p-6 max-w-screen-2xl">
          {children}
        </main>
        <Footer />
      </div>
    </div>
  );
}
