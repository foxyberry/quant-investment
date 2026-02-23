'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Activity, Play, Square, RefreshCw, ExternalLink, ShoppingCart } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import {
  getKiwoomConditionList,
  getKiwoomConditionMatches,
  startKiwoomConditionMonitor,
  stopKiwoomConditionMonitor,
} from '@/lib/api';
import type {
  KiwoomCondition,
  KiwoomConditionEvent,
  KiwoomConditionMatch,
  KiwoomConditionSignalType,
} from '@/lib/types';
import { formatCurrency as formatCurrencyUtil } from '@/lib/format';

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'fallback';

export default function ConditionMonitorPanel() {
  const t = useTranslations('screening');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency: string = 'KRW') =>
    formatCurrencyUtil(value, currency, locale);

  const [conditions, setConditions] = useState<KiwoomCondition[]>([]);
  const [selectedCondition, setSelectedCondition] = useState<KiwoomCondition | null>(null);
  const [matches, setMatches] = useState<KiwoomConditionMatch[]>([]);
  const [events, setEvents] = useState<KiwoomConditionEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const fallbackPollRef = useRef<number | null>(null);

  const loadConditions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getKiwoomConditionList();
      setConditions(data);
      if (!selectedCondition && data.length > 0) {
        setSelectedCondition(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('conditionLoadFailed'));
    } finally {
      setIsLoading(false);
    }
  }, [selectedCondition, t]);

  const loadMatches = useCallback(async () => {
    if (!selectedCondition) return;
    try {
      const data = await getKiwoomConditionMatches(selectedCondition);
      setMatches(data);
    } catch {
      // Keep current view; monitoring stream still provides updates.
    }
  }, [selectedCondition]);

  useEffect(() => {
    loadConditions();
  }, [loadConditions]);

  const handleStart = useCallback(async () => {
    if (!selectedCondition) {
      setError(t('conditionSelectRequired'));
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await startKiwoomConditionMonitor(selectedCondition);
      setIsMonitoring(true);
      setEvents([]);
      await loadMatches();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('conditionStartFailed'));
    } finally {
      setIsSubmitting(false);
    }
  }, [loadMatches, selectedCondition, t]);

  const handleStop = useCallback(async () => {
    if (!selectedCondition) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await stopKiwoomConditionMonitor(selectedCondition);
      setIsMonitoring(false);
      setConnectionState('disconnected');
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('conditionStopFailed'));
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedCondition, t]);

  const pushEvent = useCallback((signalType: KiwoomConditionSignalType, ticker: string, name?: string | null, price?: number | null) => {
    const nextEvent: KiwoomConditionEvent = {
      type: signalType,
      ticker,
      name: name ?? null,
      price: typeof price === 'number' ? price : null,
      occurred_at: new Date().toISOString(),
    };

    setEvents((prev) => [nextEvent, ...prev].slice(0, 120));

    setMatches((prev) => {
      if (signalType === 'I') {
        const found = prev.find((item) => item.ticker === ticker);
        if (found) {
          return prev.map((item) =>
            item.ticker === ticker
              ? {
                  ...item,
                  name: name ?? item.name ?? null,
                  current_price: typeof price === 'number' ? price : item.current_price ?? null,
                  updated_at: new Date().toISOString(),
                }
              : item
          );
        }
        return [
          {
            ticker,
            name: name ?? null,
            current_price: typeof price === 'number' ? price : null,
            updated_at: new Date().toISOString(),
          },
          ...prev,
        ];
      }
      return prev.filter((item) => item.ticker !== ticker);
    });
  }, []);

  useEffect(() => {
    if (!isMonitoring || !selectedCondition) return;

    const configured = process.env.NEXT_PUBLIC_KIWOOM_CONDITION_WS_URL;
    const baseUrl = configured ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
    let wsUrl: string | null = null;

    try {
      const url = new URL(baseUrl);
      if (!configured) {
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        url.pathname = '/api/kiwoom/conditions/ws';
      }
      url.searchParams.set('condition_index', String(selectedCondition.index));
      url.searchParams.set('condition_name', selectedCondition.name);
      wsUrl = url.toString();
    } catch {
      wsUrl = null;
    }

    if (!wsUrl) {
      setConnectionState('fallback');
      fallbackPollRef.current = window.setInterval(() => {
        loadMatches();
      }, 8000);
      return () => {
        if (fallbackPollRef.current) {
          window.clearInterval(fallbackPollRef.current);
          fallbackPollRef.current = null;
        }
      };
    }

    setConnectionState('connecting');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState('connected');
    };

    ws.onmessage = (event) => {
      if (typeof event.data !== 'string') return;
      try {
        const parsed = JSON.parse(event.data) as Record<string, unknown>;
        const typeRaw = parsed.type ?? parsed.signal_type;
        const tickerRaw = parsed.ticker ?? parsed.code ?? parsed.symbol;
        const nameRaw = parsed.name;
        const priceRaw = parsed.price ?? parsed.current_price;

        const type = typeRaw === 'I' || typeRaw === 'D' ? typeRaw : null;
        const ticker = typeof tickerRaw === 'string' ? tickerRaw : null;
        const price =
          typeof priceRaw === 'number'
            ? priceRaw
            : typeof priceRaw === 'string'
            ? Number(priceRaw.replace(/,/g, ''))
            : null;

        if (!type || !ticker) return;
        pushEvent(
          type,
          ticker,
          typeof nameRaw === 'string' ? nameRaw : null,
          Number.isFinite(price as number) ? (price as number) : null
        );
      } catch {
        // Ignore parse errors.
      }
    };

    const fallback = () => {
      setConnectionState('fallback');
      if (!fallbackPollRef.current) {
        fallbackPollRef.current = window.setInterval(() => {
          loadMatches();
        }, 8000);
      }
    };

    ws.onerror = fallback;
    ws.onclose = fallback;

    return () => {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      if (fallbackPollRef.current) {
        window.clearInterval(fallbackPollRef.current);
        fallbackPollRef.current = null;
      }
    };
  }, [isMonitoring, loadMatches, pushEvent, selectedCondition]);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (fallbackPollRef.current) {
        window.clearInterval(fallbackPollRef.current);
        fallbackPollRef.current = null;
      }
    };
  }, []);

  const monitoringBadgeClass = useMemo(() => {
    if (!isMonitoring) return 'bg-slate-100 text-slate-700 dark:bg-slate-800/80 dark:text-slate-200';
    if (connectionState === 'connected') {
      return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
    }
    if (connectionState === 'connecting') {
      return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
    }
    return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
  }, [connectionState, isMonitoring]);

  const handleOpenAnalysis = useCallback((ticker: string) => {
    const width = 900;
    const height = 700;
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;
    window.open(
      `/${locale}/analysis/${encodeURIComponent(ticker)}?popup=true`,
      `analysis_${ticker}`,
      `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
    );
  }, [locale]);

  return (
    <div className="space-y-4">
      <Card title={t('conditionMonitorTitle')}>
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-[var(--foreground-muted)]" />
              <span className="text-sm text-[var(--foreground-muted)]">{t('conditionMonitorSubtitle')}</span>
            </div>
            <span className={`rounded-full px-2 py-1 text-xs font-medium ${monitoringBadgeClass}`}>
              {!isMonitoring
                ? t('conditionStateStopped')
                : connectionState === 'connected'
                ? t('conditionStateLive')
                : connectionState === 'connecting'
                ? t('conditionStateConnecting')
                : t('conditionStatePolling')}
            </span>
          </div>

          <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto]">
            <select
              value={selectedCondition ? `${selectedCondition.index}|${selectedCondition.name}` : ''}
              onChange={(e) => {
                const [indexRaw, ...nameParts] = e.target.value.split('|');
                const index = Number(indexRaw);
                const name = nameParts.join('|');
                setSelectedCondition(Number.isFinite(index) ? { index, name } : null);
              }}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
              disabled={isLoading || isSubmitting}
            >
              <option value="">{t('conditionSelectPlaceholder')}</option>
              {conditions.map((condition) => (
                <option key={`${condition.index}-${condition.name}`} value={`${condition.index}|${condition.name}`}>
                  [{condition.index}] {condition.name}
                </option>
              ))}
            </select>

            <Button variant="outline" onClick={loadConditions} disabled={isSubmitting || isLoading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('refreshConditions')}
            </Button>

            {!isMonitoring ? (
              <Button variant="primary" onClick={handleStart} disabled={isSubmitting || !selectedCondition}>
                <Play className="mr-2 h-4 w-4" />
                {t('startMonitor')}
              </Button>
            ) : (
              <Button variant="outline" onClick={handleStop} disabled={isSubmitting}>
                <Square className="mr-2 h-4 w-4" />
                {t('stopMonitor')}
              </Button>
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-200">
              {error}
            </div>
          )}
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title={t('conditionTimelineTitle')}>
          <div className="max-h-[340px] space-y-2 overflow-y-auto pr-1">
            {events.length === 0 ? (
              <p className="text-sm text-[var(--foreground-muted)]">{t('conditionTimelineEmpty')}</p>
            ) : (
              events.map((event, index) => (
                <div
                  key={`${event.ticker}-${event.occurred_at}-${index}`}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    event.type === 'I'
                      ? 'border-red-200 bg-red-50/70 dark:border-red-900/40 dark:bg-red-900/20'
                      : 'border-blue-200 bg-blue-50/70 dark:border-blue-900/40 dark:bg-blue-900/20'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${event.type === 'I' ? 'bg-red-200/80 text-red-700 dark:bg-red-900/50 dark:text-red-200' : 'bg-blue-200/80 text-blue-700 dark:bg-blue-900/50 dark:text-blue-200'}`}>
                        {event.type}
                      </span>
                      <span className="font-mono text-[var(--foreground)]">{event.ticker}</span>
                      <span className="text-[var(--foreground-muted)]">{event.name ?? '-'}</span>
                    </div>
                    <span className="text-xs text-[var(--foreground-muted)]">
                      {new Date(event.occurred_at).toLocaleTimeString(locale)}
                    </span>
                  </div>
                  {typeof event.price === 'number' && (
                    <p className="mt-1 font-mono text-xs text-[var(--foreground-muted)]">
                      {formatCurrency(event.price, 'KRW')}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>

        <Card title={t('conditionMatchesTitle')}>
          <div className="max-h-[340px] overflow-auto">
            {matches.length === 0 ? (
              <p className="text-sm text-[var(--foreground-muted)]">{t('conditionMatchesEmpty')}</p>
            ) : (
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--foreground-muted)]">
                    <th className="px-2 py-2 font-medium">{t('ticker')}</th>
                    <th className="px-2 py-2 font-medium">{t('name')}</th>
                    <th className="px-2 py-2 text-right font-medium">{t('price')}</th>
                    <th className="px-2 py-2 text-right font-medium">{t('actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {matches.map((stock) => (
                    <tr key={stock.ticker} className="border-b border-[var(--border)]/70">
                      <td className="px-2 py-2 font-mono text-[var(--color-primary)]">{stock.ticker}</td>
                      <td className="px-2 py-2 text-[var(--foreground)]">{stock.name ?? '-'}</td>
                      <td className="px-2 py-2 text-right font-mono text-[var(--foreground)]">
                        {formatCurrency(stock.current_price ?? null, 'KRW')}
                      </td>
                      <td className="px-2 py-2">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => handleOpenAnalysis(stock.ticker)}
                            className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)]"
                            aria-label={`open-analysis-${stock.ticker}`}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            className="rounded p-1.5 text-[var(--foreground-muted)] opacity-60"
                            aria-label={`open-order-${stock.ticker}`}
                            title={t('orderComingSoon')}
                            disabled
                          >
                            <ShoppingCart className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
