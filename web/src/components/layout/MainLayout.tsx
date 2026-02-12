'use client';

import { useState, ReactNode } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import Footer from './Footer';

interface MainLayoutProps {
  children: ReactNode;
}

/**
 * Main layout wrapper that combines Header, Sidebar, and Footer
 * Handles mobile sidebar state
 */
export default function MainLayout({ children }: MainLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setIsSidebarOpen(false);

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
