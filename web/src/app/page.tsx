'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui';
import {
  PortfolioSummaryCard,
  SellSignalsCard,
  RecentReportsCard,
  QuickActionsCard,
} from '@/components/dashboard';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';

interface ConnectionStatus {
  connected: boolean;
  checking: boolean;
  error?: string;
}

export default function Home() {
  const [status, setStatus] = useState<ConnectionStatus>({
    connected: false,
    checking: true,
  });

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(5000),
        });

        if (response.ok) {
          setStatus({ connected: true, checking: false });
        } else {
          setStatus({
            connected: false,
            checking: false,
            error: `Server returned ${response.status}`,
          });
        }
      } catch {
        setStatus({
          connected: false,
          checking: false,
          error: 'Unable to connect to API server',
        });
      }
    };

    checkConnection();
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Dashboard</h1>
          <p className="text-[var(--foreground-muted)] mt-1">
            Welcome to your quantitative investment dashboard
          </p>
        </div>

        {/* Connection Status Badge */}
        <div className="flex items-center gap-2">
          {status.checking ? (
            <div className="flex items-center gap-2 rounded-full bg-yellow-100 px-3 py-1.5 text-sm text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Connecting...</span>
            </div>
          ) : status.connected ? (
            <div className="flex items-center gap-2 rounded-full bg-green-100 px-3 py-1.5 text-sm text-green-800 dark:bg-green-900 dark:text-green-200">
              <Wifi className="h-4 w-4" />
              <span>API Connected</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-full bg-red-100 px-3 py-1.5 text-sm text-red-800 dark:bg-red-900 dark:text-red-200">
              <WifiOff className="h-4 w-4" />
              <span>API Disconnected</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Portfolio Summary - Full width on mobile, left column on desktop */}
        <PortfolioSummaryCard />

        {/* Sell Signals Alert */}
        <SellSignalsCard />

        {/* Recent Reports */}
        <RecentReportsCard />

        {/* Quick Actions */}
        <QuickActionsCard />
      </div>

      {/* Getting Started Info - Shown when API is not connected */}
      {!status.checking && !status.connected && (
        <Card>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 rounded-lg bg-blue-100 p-2 dark:bg-blue-900">
              <WifiOff className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="font-semibold text-[var(--foreground)]">
                Getting Started
              </h3>
              <p className="mt-1 text-sm text-[var(--foreground-muted)]">
                This dashboard connects to the FastAPI backend at{' '}
                <code className="rounded bg-[var(--background)] px-1.5 py-0.5 font-mono text-xs">
                  {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                </code>
                . Make sure the API server is running to see live data.
              </p>
              <p className="mt-2 text-sm text-[var(--foreground-muted)]">
                Start the API server with:{' '}
                <code className="rounded bg-[var(--background)] px-1.5 py-0.5 font-mono text-xs">
                  python -m uvicorn api.main:app --reload
                </code>
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
