'use client';

import { useEffect, useState } from 'react';

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
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      {/* Header */}
      <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
            Quant Investment Dashboard
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* API Connection Status */}
        <div className="mb-8 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            API Connection Status
          </h2>
          <div className="flex items-center gap-3">
            {status.checking ? (
              <>
                <div className="h-3 w-3 animate-pulse rounded-full bg-yellow-500" />
                <span className="text-zinc-600 dark:text-zinc-400">
                  Checking connection...
                </span>
              </>
            ) : status.connected ? (
              <>
                <div className="h-3 w-3 rounded-full bg-green-500" />
                <span className="text-zinc-600 dark:text-zinc-400">
                  Connected to API server
                </span>
              </>
            ) : (
              <>
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <span className="text-zinc-600 dark:text-zinc-400">
                  {status.error || 'Disconnected'}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Dashboard Placeholder Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Portfolio Overview Card */}
          <div className="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
            <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
              Portfolio Overview
            </h3>
            <p className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
              --
            </p>
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
              Coming soon
            </p>
          </div>

          {/* Screening Results Card */}
          <div className="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
            <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
              Screening Results
            </h3>
            <p className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
              --
            </p>
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
              Coming soon
            </p>
          </div>

          {/* Market Status Card */}
          <div className="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
            <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">
              Market Status
            </h3>
            <p className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
              --
            </p>
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
              Coming soon
            </p>
          </div>
        </div>

        {/* Info Section */}
        <div className="mt-8 rounded-lg border border-blue-200 bg-blue-50 p-6 dark:border-blue-900 dark:bg-blue-950">
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
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
            Quant Investment System
          </p>
        </div>
      </footer>
    </div>
  );
}
