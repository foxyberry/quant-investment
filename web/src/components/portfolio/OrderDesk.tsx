'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { AlertTriangle, Pencil, RefreshCw, ShieldAlert, XCircle } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import {
  amendKiwoomOrder,
  cancelKiwoomOrder,
  getKiwoomConnectionStatus,
  getKiwoomOrders,
  placeKiwoomOrder,
  triggerKiwoomKillSwitch,
} from '@/lib/api';
import type { KiwoomOrder, KiwoomOrderRequest, KiwoomOrderStatus } from '@/lib/types';
import { formatCurrency as formatCurrencyUtil } from '@/lib/format';

type ConnectionMode = 'disconnected' | 'connecting' | 'connected' | 'fallback';

const ORDER_STATUSES: KiwoomOrderStatus[] = [
  'RECEIVED',
  'CONFIRMED',
  'PARTIAL',
  'FILLED',
  'CANCELED',
  'REJECTED',
];

interface OrderDeskPrefill {
  ticker: string;
  currentPrice: number | null;
  currency?: string | null;
  name?: string | null;
  updatedAt: number;
}

interface OrderDeskProps {
  prefill?: OrderDeskPrefill | null;
}

export default function OrderDesk({ prefill }: OrderDeskProps) {
  const t = useTranslations('portfolio');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency: string = 'KRW') =>
    formatCurrencyUtil(value, currency, locale);

  const [orders, setOrders] = useState<KiwoomOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionMode, setConnectionMode] = useState<ConnectionMode>('disconnected');

  const [ticker, setTicker] = useState('');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('1');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('LIMIT');
  const [price, setPrice] = useState('');

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingOrderRequest, setPendingOrderRequest] = useState<KiwoomOrderRequest | null>(null);

  const [amendTarget, setAmendTarget] = useState<KiwoomOrder | null>(null);
  const [amendQty, setAmendQty] = useState('');
  const [amendPrice, setAmendPrice] = useState('');

  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);

  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_CAP_MS = 30_000;

  useEffect(() => {
    if (!prefill?.ticker) return;
    setTicker(prefill.ticker.toUpperCase());
    if (orderType === 'LIMIT' && prefill.currentPrice !== null && Number.isFinite(prefill.currentPrice)) {
      setPrice(String(prefill.currentPrice));
    }
    setError(null);
  }, [orderType, prefill]);

  const loadOrders = useCallback(async () => {
    try {
      const data = await getKiwoomOrders();
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('orderLoadFailed'));
    }
  }, [t]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setIsLoading(true);
      try {
        const data = await getKiwoomOrders();
        if (mounted) {
          setOrders(data);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : t('orderLoadFailed'));
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, [t]);

  useEffect(() => {
    let unmounted = false;

    const configured = process.env.NEXT_PUBLIC_KIWOOM_ORDERS_WS_URL;
    const baseUrl = configured ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
    let wsUrl: string | null = null;

    try {
      const url = new URL(baseUrl);
      if (!configured) {
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        url.pathname = '/api/kiwoom/orders/ws';
      }
      wsUrl = url.toString();
    } catch {
      wsUrl = null;
    }

    if (!wsUrl) {
      setConnectionMode('fallback');
      pollRef.current = window.setInterval(loadOrders, 5000);
      return () => {
        if (pollRef.current) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };
    }

    const startPollingFallback = () => {
      setConnectionMode('fallback');
      if (!pollRef.current) {
        pollRef.current = window.setInterval(loadOrders, 5000);
      }
    };

    const stopPolling = () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    const connectWs = () => {
      if (unmounted) return;

      setConnectionMode('connecting');
      const ws = new WebSocket(wsUrl!);
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmounted) return;
        reconnectAttemptRef.current = 0;
        setConnectionMode('connected');
        stopPolling();
      };

      ws.onmessage = (event) => {
        if (typeof event.data !== 'string') return;
        try {
          const parsed = JSON.parse(event.data) as unknown;
          const payload = parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
          const ordersPayload = Array.isArray(payload?.orders)
            ? payload?.orders
            : Array.isArray(payload?.data)
            ? payload?.data
            : Array.isArray(parsed)
            ? parsed
            : null;

          if (ordersPayload) {
            void loadOrders();
            return;
          }

          const one = payload?.order && typeof payload.order === 'object' ? payload.order : payload;
          if (one && typeof one === 'object') {
            void loadOrders();
          }
        } catch {
          // ignore malformed messages
        }
      };

      const handleWsClose = () => {
        if (unmounted) return;

        // Null out listeners on the closed socket to prevent duplicate handling
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;

        if (wsRef.current === ws) {
          wsRef.current = null;
        }

        const attempt = reconnectAttemptRef.current;
        if (attempt >= MAX_RECONNECT_ATTEMPTS) {
          startPollingFallback();
          return;
        }

        setConnectionMode('connecting');
        const delayMs = Math.min(1000 * Math.pow(2, attempt), RECONNECT_CAP_MS);
        reconnectAttemptRef.current = attempt + 1;

        reconnectTimerRef.current = window.setTimeout(() => {
          reconnectTimerRef.current = null;
          connectWs();
        }, delayMs);
      };

      ws.onerror = () => {
        // onerror is always followed by onclose; let onclose handle reconnection.
      };
      ws.onclose = handleWsClose;
    };

    connectWs();

    return () => {
      unmounted = true;

      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      const ws = wsRef.current;
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        ws.close();
        wsRef.current = null;
      }

      stopPolling();
    };
  }, [loadOrders]);

  const submitOrder = useCallback(
    async (request: KiwoomOrderRequest) => {
      setIsSubmitting(true);
      setError(null);
      try {
        await placeKiwoomOrder(request);
        setTicker('');
        setQuantity('1');
        setOrderType('LIMIT');
        setPrice('');
        await loadOrders();
      } catch (err) {
        setError(err instanceof Error ? err.message : t('orderSubmitFailed'));
      } finally {
        setIsSubmitting(false);
      }
    },
    [loadOrders, t]
  );

  const handleSubmit = useCallback(async () => {
    const qty = Number(quantity);
    const px = Number(price);

    if (!ticker.trim()) {
      setError(t('orderTickerRequired'));
      return;
    }
    if (!Number.isFinite(qty) || qty <= 0) {
      setError(t('orderQuantityInvalid'));
      return;
    }
    if (orderType === 'LIMIT' && (!Number.isFinite(px) || px <= 0)) {
      setError(t('orderPriceInvalid'));
      return;
    }

    const request: KiwoomOrderRequest = {
      ticker: ticker.trim().toUpperCase(),
      side,
      quantity: qty,
      order_type: orderType,
      price: orderType === 'LIMIT' ? px : null,
    };

    try {
      const status = await getKiwoomConnectionStatus();
      if (status.is_mock_trading === false) {
        setPendingOrderRequest(request);
        setConfirmOpen(true);
        return;
      }
    } catch {
      // If status check fails, continue as mock-safe path.
    }

    await submitOrder(request);
  }, [orderType, price, quantity, side, submitOrder, t, ticker]);

  const confirmRealOrder = useCallback(async () => {
    if (!pendingOrderRequest) return;
    setConfirmOpen(false);
    await submitOrder(pendingOrderRequest);
    setPendingOrderRequest(null);
  }, [pendingOrderRequest, submitOrder]);

  const handleCancelOrder = useCallback(
    async (orderId: string) => {
      setIsSubmitting(true);
      setError(null);
      try {
        await cancelKiwoomOrder(orderId);
        await loadOrders();
      } catch (err) {
        setError(err instanceof Error ? err.message : t('orderCancelFailed'));
      } finally {
        setIsSubmitting(false);
      }
    },
    [loadOrders, t]
  );

  const openAmend = useCallback((order: KiwoomOrder) => {
    setAmendTarget(order);
    setAmendQty(String(order.unfilled_quantity || order.quantity));
    setAmendPrice(order.price ? String(order.price) : '');
  }, []);

  const submitAmend = useCallback(async () => {
    if (!amendTarget) return;
    const qtyNum = Number(amendQty);
    const priceNum = amendPrice ? Number(amendPrice) : null;

    if (!Number.isFinite(qtyNum) || qtyNum <= 0) {
      setError(t('orderQuantityInvalid'));
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await amendKiwoomOrder(amendTarget.order_id, {
        quantity: qtyNum,
        price: Number.isFinite(priceNum as number) ? (priceNum as number) : null,
      });
      setAmendTarget(null);
      await loadOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('orderAmendFailed'));
    } finally {
      setIsSubmitting(false);
    }
  }, [amendPrice, amendQty, amendTarget, loadOrders, t]);

  const handleKillSwitch = useCallback(async () => {
    if (!window.confirm(t('killSwitchConfirm'))) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await triggerKiwoomKillSwitch();
      await loadOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('killSwitchFailed'));
    } finally {
      setIsSubmitting(false);
    }
  }, [loadOrders, t]);

  const connectionLabel = useMemo(() => {
    if (connectionMode === 'connected') return t('orderRealtimeLive');
    if (connectionMode === 'connecting') return t('orderRealtimeConnecting');
    if (connectionMode === 'fallback') return t('orderRealtimePolling');
    return t('orderRealtimeOffline');
  }, [connectionMode, t]);

  const statusBadgeClass = (status: KiwoomOrderStatus) => {
    if (status === 'FILLED') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
    if (status === 'CANCELED' || status === 'REJECTED') {
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
    }
    if (status === 'PARTIAL') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
    return 'bg-slate-100 text-slate-700 dark:bg-slate-800/80 dark:text-slate-200';
  };

  return (
    <div className="space-y-4">
      <Card title={t('orderDeskTitle')}>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm text-[var(--foreground-muted)]">{t('orderDeskSubtitle')}</span>
            <span className="rounded-full bg-[var(--background)] px-2 py-1 text-xs text-[var(--foreground-muted)]">
              {connectionLabel}
            </span>
          </div>

          {prefill && (
            <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm">
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className="text-[var(--foreground-muted)]">
                  {t('ticker')}: <span className="font-mono text-[var(--foreground)]">{prefill.ticker}</span>
                </span>
                <span className="text-[var(--foreground-muted)]">
                  {t('currentPrice')}:{' '}
                  <span className="font-mono text-[var(--foreground)]">
                    {formatCurrency(prefill.currentPrice, prefill.currency ?? 'KRW')}
                  </span>
                </span>
                {prefill.name && (
                  <span className="text-[var(--foreground-muted)]">
                    {t('name')}: <span className="text-[var(--foreground)]">{prefill.name}</span>
                  </span>
                )}
              </div>
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder={t('orderTicker')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            />
            <select
              value={side}
              onChange={(e) => setSide(e.target.value === 'SELL' ? 'SELL' : 'BUY')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            >
              <option value="BUY">{t('orderSideBuy')}</option>
              <option value="SELL">{t('orderSideSell')}</option>
            </select>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder={t('orderQuantity')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            />
            <select
              value={orderType}
              onChange={(e) => setOrderType(e.target.value === 'MARKET' ? 'MARKET' : 'LIMIT')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            >
              <option value="LIMIT">{t('orderTypeLimit')}</option>
              <option value="MARKET">{t('orderTypeMarket')}</option>
            </select>
            <input
              type="number"
              min={0}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={t('orderPrice')}
              disabled={orderType === 'MARKET'}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm disabled:opacity-50"
            />
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {t('orderSubmit')}
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={loadOrders} disabled={isSubmitting || isLoading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('orderRefresh')}
            </Button>
            <Button variant="outline" onClick={handleKillSwitch} disabled={isSubmitting}>
              <ShieldAlert className="mr-2 h-4 w-4" />
              {t('killSwitch')}
            </Button>
          </div>

          {error && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-200">
              {error}
            </div>
          )}
        </div>
      </Card>

      <Card title={t('orderHistoryTitle')}>
        {isLoading ? (
          <p className="text-sm text-[var(--foreground-muted)]">{t('orderLoading')}</p>
        ) : orders.length === 0 ? (
          <p className="text-sm text-[var(--foreground-muted)]">{t('orderEmpty')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[940px] text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--foreground-muted)]">
                  <th className="px-2 py-2 font-medium">{t('orderId')}</th>
                  <th className="px-2 py-2 font-medium">{t('ticker')}</th>
                  <th className="px-2 py-2 font-medium">{t('orderSide')}</th>
                  <th className="px-2 py-2 text-right font-medium">{t('orderQuantity')}</th>
                  <th className="px-2 py-2 text-right font-medium">{t('orderFilledPrice')}</th>
                  <th className="px-2 py-2 text-right font-medium">{t('orderUnfilledQty')}</th>
                  <th className="px-2 py-2 font-medium">{t('orderStatus')}</th>
                  <th className="px-2 py-2 text-right font-medium">{t('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => {
                  const canChange = ['RECEIVED', 'CONFIRMED', 'PARTIAL'].includes(order.status);
                  return (
                    <tr key={order.order_id} className="border-b border-[var(--border)]/70">
                      <td className="px-2 py-2 font-mono text-xs text-[var(--foreground)]">{order.order_id}</td>
                      <td className="px-2 py-2 font-mono text-[var(--color-primary)]">{order.ticker}</td>
                      <td className="px-2 py-2">{order.side === 'BUY' ? t('orderSideBuy') : t('orderSideSell')}</td>
                      <td className="px-2 py-2 text-right font-mono">{order.quantity.toLocaleString(locale)}</td>
                      <td className="px-2 py-2 text-right font-mono">{formatCurrency(order.filled_price ?? order.price, 'KRW')}</td>
                      <td className="px-2 py-2 text-right font-mono">{order.unfilled_quantity.toLocaleString(locale)}</td>
                      <td className="px-2 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs ${statusBadgeClass(order.status)}`}>
                          {t(`orderStatus_${order.status}`)}
                        </span>
                      </td>
                      <td className="px-2 py-2">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            disabled={!canChange || isSubmitting}
                            onClick={() => openAmend(order)}
                            className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-[var(--border)] disabled:opacity-40"
                            aria-label={`amend-${order.order_id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            disabled={!canChange || isSubmitting}
                            onClick={() => handleCancelOrder(order.order_id)}
                            className="rounded p-1.5 text-[var(--foreground-muted)] hover:bg-red-100 hover:text-red-700 disabled:opacity-40 dark:hover:bg-red-900/30"
                            aria-label={`cancel-${order.order_id}`}
                          >
                            <XCircle className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {confirmOpen && pendingOrderRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-5 shadow-xl">
            <div className="mb-3 flex items-center gap-2 text-red-600 dark:text-red-300">
              <AlertTriangle className="h-5 w-5" />
              <h3 className="font-semibold">{t('orderConfirmTitle')}</h3>
            </div>
            <p className="text-sm text-[var(--foreground-muted)]">{t('orderConfirmLiveWarning')}</p>
            <div className="mt-4 rounded-lg border border-[var(--border)] p-3 text-sm">
              <p>{t('ticker')}: <span className="font-mono">{pendingOrderRequest.ticker}</span></p>
              <p>{t('orderSide')}: {pendingOrderRequest.side === 'BUY' ? t('orderSideBuy') : t('orderSideSell')}</p>
              <p>{t('orderQuantity')}: {pendingOrderRequest.quantity.toLocaleString(locale)}</p>
              <p>{t('orderType')}: {pendingOrderRequest.order_type === 'MARKET' ? t('orderTypeMarket') : t('orderTypeLimit')}</p>
              <p>{t('orderPrice')}: {pendingOrderRequest.order_type === 'MARKET' ? '-' : formatCurrency(pendingOrderRequest.price ?? null, 'KRW')}</p>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setConfirmOpen(false);
                  setPendingOrderRequest(null);
                }}
              >
                {tCommon('cancel')}
              </Button>
              <Button onClick={confirmRealOrder}>
                {tCommon('confirm')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {amendTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-5 shadow-xl">
            <h3 className="font-semibold text-[var(--foreground)]">{t('orderAmendTitle')}</h3>
            <p className="mt-1 text-sm text-[var(--foreground-muted)]">{amendTarget.order_id}</p>
            <div className="mt-4 grid gap-3">
              <input
                type="number"
                min={1}
                value={amendQty}
                onChange={(e) => setAmendQty(e.target.value)}
                placeholder={t('orderQuantity')}
                className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
              />
              <input
                type="number"
                min={0}
                value={amendPrice}
                onChange={(e) => setAmendPrice(e.target.value)}
                placeholder={t('orderPrice')}
                className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setAmendTarget(null)}>
                {tCommon('cancel')}
              </Button>
              <Button onClick={submitAmend} disabled={isSubmitting}>
                {tCommon('save')}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="sr-only">
        {ORDER_STATUSES.map((status) => (
          <span key={status}>{t(`orderStatus_${status}`)}</span>
        ))}
      </div>
    </div>
  );
}
