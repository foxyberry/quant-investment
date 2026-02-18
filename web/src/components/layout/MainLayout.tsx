'use client';

import { useState, ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';
import Header from './Header';
import Sidebar from './Sidebar';
import Footer from './Footer';

interface MainLayoutProps {
  children: ReactNode;
}

/**
 * Main layout wrapper that combines Header, Sidebar, and Footer
 * Handles mobile sidebar state
 * When popup=true query param is present, renders content only (no navigation)
 */
export default function MainLayout({ children }: MainLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const searchParams = useSearchParams();
  const isPopup = searchParams.get('popup') === 'true';

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setIsSidebarOpen(false);

  if (isPopup) {
    return <main className="min-h-screen p-4">{children}</main>;
  }

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <Header onMenuClick={toggleSidebar} isSidebarOpen={isSidebarOpen} />
      <Sidebar isOpen={isSidebarOpen} onClose={closeSidebar} />

      {/* Main content area */}
      <div className="lg:ml-[var(--sidebar-width)] pt-[var(--header-height)] min-h-screen flex flex-col transition-sidebar">
        <main className="flex-1 p-4 lg:p-6">
          {children}
        </main>
        <Footer />
      </div>
    </div>
  );
}
