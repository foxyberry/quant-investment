'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui';

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
            error: `Server returned ${response.status}`
          });
        }
      } catch {
        setStatus({
          connected: false,
          checking: false,
          error: 'Unable to connect to API server'
        });
      }
    };

    checkConnection();
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Dashboard</h1>
        <p className="text-[var(--foreground-muted)] mt-1">
          Welcome to your quantitative investment dashboard
        </p>
      </div>

      {/* API Connection Status */}
      <Card title="API Connection Status">
        <div className="flex items-center gap-3">
          {status.checking ? (
            <>
              <div className="h-3 w-3 animate-pulse rounded-full bg-yellow-500" />
              <span className="text-[var(--foreground-muted)]">
                Checking connection...
              </span>
            </>
          ) : status.connected ? (
            <>
              <div className="h-3 w-3 rounded-full bg-green-500" />
              <span className="text-[var(--foreground-muted)]">
                Connected to API server
              </span>
            </>
          ) : (
            <>
              <div className="h-3 w-3 rounded-full bg-red-500" />
              <span className="text-[var(--foreground-muted)]">
                {status.error || 'Disconnected'}
              </span>
            </>
          )}
        </div>
      </Card>

      {/* Dashboard Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Portfolio Overview Card */}
        <Card title="Portfolio Overview">
          <p className="text-3xl font-semibold text-[var(--foreground)]">
            --
          </p>
          <p className="mt-2 text-sm text-[var(--foreground-muted)]">
            Coming soon
          </p>
        </Card>

        {/* Screening Results Card */}
        <Card title="Screening Results">
          <p className="text-3xl font-semibold text-[var(--foreground)]">
            --
          </p>
          <p className="mt-2 text-sm text-[var(--foreground-muted)]">
            Coming soon
          </p>
        </Card>

        {/* Market Status Card */}
        <Card title="Market Status">
          <p className="text-3xl font-semibold text-[var(--foreground)]">
            --
          </p>
          <p className="mt-2 text-sm text-[var(--foreground-muted)]">
            Coming soon
          </p>
        </Card>
      </div>

      {/* Getting Started Info */}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-6 dark:border-blue-900 dark:bg-blue-950">
        <h3 className="mb-2 font-semibold text-blue-900 dark:text-blue-100">
          Getting Started
        </h3>
        <p className="text-sm text-blue-800 dark:text-blue-200">
          This dashboard connects to the FastAPI backend at{' '}
          <code className="rounded bg-blue-100 px-1 py-0.5 font-mono text-xs dark:bg-blue-900">
            {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
          </code>
          . Make sure the API server is running to see live data.
        </p>
      </div>
    </div>
  );
}
