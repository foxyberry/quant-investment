'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { AlertTriangle, Pencil, RefreshCw, ShieldAlert, XCircle } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import {
  amendBrokerOrder,
  cancelBrokerOrder,
  getBrokerConnectionStatus,
  getBrokerOrders,
  listBrokers,
  placeBrokerOrder,
  triggerBrokerKillSwitch,
} from '@/lib/api';
import type {
  BrokerConnectionState,
  BrokerOrder,
  BrokerOrderRequest,
  BrokerOrderStatus,
} from '@/lib/types';
import { formatCurrency as formatCurrencyUtil } from '@/lib/format';

const ORDER_STATUSES: BrokerOrderStatus[] = [
  'RECEIVED',
  'CONFIRMED',
  'PARTIAL',
  'FILLED',
  'CANCELED',
  'REJECTED',
];

export default function BrokerOrderDesk() {
  const t = useTranslations('brokerOrderDesk');
  const tPortfolio = useTranslations('portfolio');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const formatCurrency = (value: number | null, currency: string = 'USD') =>
    formatCurrencyUtil(value, currency, locale);

  // Broker selection
  const [brokers, setBrokers] = useState<string[]>([]);
  const [selectedBroker, setSelectedBroker] = useState<string>('');
  const [connectionState, setConnectionState] = useState<BrokerConnectionState>('unavailable');
  const [isPaperTrading, setIsPaperTrading] = useState<boolean | null>(null);

  // Orders
  const [orders, setOrders] = useState<BrokerOrder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form state
  const [ticker, setTicker] = useState('');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState('1');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [price, setPrice] = useState('');

  // Confirm dialog
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingOrderRequest, setPendingOrderRequest] = useState<BrokerOrderRequest | null>(null);

  // Amend dialog
  const [amendTarget, setAmendTarget] = useState<BrokerOrder | null>(null);
  const [amendQty, setAmendQty] = useState('');
  const [amendPrice, setAmendPrice] = useState('');

  // Polling
  const pollRef = useRef<number | null>(null);

  // Load available brokers
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const list = await listBrokers();
        if (mounted && list.length > 0) {
          setBrokers(list);
          setSelectedBroker(list[0]);
        }
      } catch {
        // Broker list unavailable
      }
    })();
    return () => { mounted = false; };
  }, []);

  // Load connection status when broker changes
  useEffect(() => {
    if (!selectedBroker) return;
    let mounted = true;
    (async () => {
      try {
        const status = await getBrokerConnectionStatus(selectedBroker);
        if (mounted) {
          setConnectionState(status.status);
          setIsPaperTrading(status.is_paper_trading);
        }
      } catch {
        if (mounted) {
          setConnectionState('unavailable');
          setIsPaperTrading(null);
        }
      }
    })();
    return () => { mounted = false; };
  }, [selectedBroker]);

  const loadOrders = useCallback(async () => {
    if (!selectedBroker) return;
    try {
      const data = await getBrokerOrders(selectedBroker);
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('orderLoadFailed'));
    }
  }, [selectedBroker, t]);

  // Load orders when broker changes
  useEffect(() => {
    if (!selectedBroker) return;
    let mounted = true;
    (async () => {
      setIsLoading(true);
      setOrders([]);
      setError(null);
      try {
        const data = await getBrokerOrders(selectedBroker);
        if (mounted) {
          setOrders(data);
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
    return () => { mounted = false; };
  }, [selectedBroker, t]);

  // HTTP polling for order updates
  useEffect(() => {
    if (!selectedBroker) return;
    pollRef.current = window.setInterval(loadOrders, 5000);
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [selectedBroker, loadOrders]);

  const showSuccess = useCallback((msg: string) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 3000);
  }, []);

  const handleSubmit = useCallback(async () => {
    const qty = Number(quantity);
    const px = Number(price);

    if (!selectedBroker) {
      setError(t('selectBroker'));
      return;
    }
    if (!ticker.trim()) {
      setError(tPortfolio('orderTickerRequired'));
      return;
    }
    if (!Number.isFinite(qty) || qty <= 0) {
      setError(tPortfolio('orderQuantityInvalid'));
      return;
    }
    if (orderType === 'LIMIT' && (!Number.isFinite(px) || px <= 0)) {
      setError(tPortfolio('orderPriceInvalid'));
      return;
    }

    const request: BrokerOrderRequest = {
      ticker: ticker.trim().toUpperCase(),
      side,
      quantity: qty,
      order_type: orderType,
      price: orderType === 'LIMIT' ? px : null,
    };

    // If not paper trading, require confirmation
    if (isPaperTrading === false) {
      setPendingOrderRequest(request);
      setConfirmOpen(true);
      return;
    }

    await submitOrder(request);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- submitOrder is defined below, stable ref
  }, [isPaperTrading, orderType, price, quantity, selectedBroker, side, t, tPortfolio, ticker]);

  const submitOrder = useCallback(
    async (request: BrokerOrderRequest) => {
      setIsSubmitting(true);
      setError(null);
      try {
        await placeBrokerOrder(selectedBroker, request);
        setTicker('');
        setQuantity('1');
        setOrderType('MARKET');
        setPrice('');
        showSuccess(t('orderPlaced'));
        await loadOrders();
      } catch (err) {
        setError(err instanceof Error ? err.message : tPortfolio('orderSubmitFailed'));
      } finally {
        setIsSubmitting(false);
      }
    },
    [loadOrders, selectedBroker, showSuccess, t, tPortfolio]
  );

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
        await cancelBrokerOrder(selectedBroker, orderId);
        showSuccess(t('orderCancelled'));
        await loadOrders();
      } catch (err) {
        setError(err instanceof Error ? err.message : tPortfolio('orderCancelFailed'));
      } finally {
        setIsSubmitting(false);
      }
    },
    [loadOrders, selectedBroker, showSuccess, t, tPortfolio]
  );

  const openAmend = useCallback((order: BrokerOrder) => {
    setAmendTarget(order);
    setAmendQty(String(order.unfilled_quantity || order.quantity));
    setAmendPrice(order.price ? String(order.price) : '');
  }, []);

  const submitAmend = useCallback(async () => {
    if (!amendTarget) return;
    const qtyNum = Number(amendQty);
    const priceNum = amendPrice ? Number(amendPrice) : null;

    if (!Number.isFinite(qtyNum) || qtyNum <= 0) {
      setError(tPortfolio('orderQuantityInvalid'));
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await amendBrokerOrder(selectedBroker, amendTarget.order_id, {
        quantity: qtyNum,
        price: Number.isFinite(priceNum as number) ? (priceNum as number) : undefined,
      });
      setAmendTarget(null);
      showSuccess(t('orderAmended'));
      await loadOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : tPortfolio('orderAmendFailed'));
    } finally {
      setIsSubmitting(false);
    }
  }, [amendPrice, amendQty, amendTarget, loadOrders, selectedBroker, showSuccess, t, tPortfolio]);

  const handleKillSwitch = useCallback(async () => {
    if (!window.confirm(t('killSwitchConfirm'))) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const result = await triggerBrokerKillSwitch(selectedBroker);
      showSuccess(
        `Kill switch activated. ${result.cancelled_orders} order(s) cancelled.`
      );
      await loadOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : tPortfolio('killSwitchFailed'));
    } finally {
      setIsSubmitting(false);
    }
  }, [loadOrders, selectedBroker, showSuccess, t, tPortfolio]);

  const connectionBadge = useMemo(() => {
    const label = t(connectionState);
    const cls =
      connectionState === 'connected'
        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
        : connectionState === 'disconnected'
        ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
        : 'bg-slate-100 text-slate-700 dark:bg-slate-800/80 dark:text-slate-200';
    return { label, cls };
  }, [connectionState, t]);

  const statusBadgeClass = (status: BrokerOrderStatus) => {
    if (status === 'FILLED')
      return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
    if (status === 'CANCELED' || status === 'REJECTED')
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
    if (status === 'PARTIAL')
      return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
    return 'bg-slate-100 text-slate-700 dark:bg-slate-800/80 dark:text-slate-200';
  };

  if (brokers.length === 0) {
    return (
      <Card title={t('title')}>
        <p className="text-sm text-[var(--foreground-muted)]">
          {t('noBrokers')}
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card title={t('title')}>
        <div className="space-y-4">
          {/* Broker selector + connection status */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-3">
              <label htmlFor="broker-select" className="text-sm text-[var(--foreground-muted)]">
                {t('selectBroker')}
              </label>
              <select
                id="broker-select"
                value={selectedBroker}
                onChange={(e) => setSelectedBroker(e.target.value)}
                className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
              >
                {brokers.map((b) => (
                  <option key={b} value={b}>
                    {b.charAt(0).toUpperCase() + b.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <span className={`rounded-full px-2 py-1 text-xs ${connectionBadge.cls}`}>
              {connectionBadge.label}
              {isPaperTrading === true && ' (Paper)'}
            </span>
          </div>

          {/* Order form */}
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder={tPortfolio('orderTicker')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            />
            <select
              value={side}
              onChange={(e) => setSide(e.target.value === 'SELL' ? 'SELL' : 'BUY')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            >
              <option value="BUY">{tPortfolio('orderSideBuy')}</option>
              <option value="SELL">{tPortfolio('orderSideSell')}</option>
            </select>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder={tPortfolio('orderQuantity')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            />
            <select
              value={orderType}
              onChange={(e) => setOrderType(e.target.value === 'LIMIT' ? 'LIMIT' : 'MARKET')}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
            >
              <option value="MARKET">{tPortfolio('orderTypeMarket')}</option>
              <option value="LIMIT">{tPortfolio('orderTypeLimit')}</option>
            </select>
            <input
              type="number"
              min={0}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={tPortfolio('orderPrice')}
              disabled={orderType === 'MARKET'}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm disabled:opacity-50"
            />
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {t('placeOrder')}
            </Button>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={loadOrders} disabled={isSubmitting || isLoading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {tPortfolio('orderRefresh')}
            </Button>
            <Button variant="outline" onClick={handleKillSwitch} disabled={isSubmitting}>
              <ShieldAlert className="mr-2 h-4 w-4" />
              {t('killSwitch')}
            </Button>
          </div>

          {/* Success message */}
          {successMessage && (
            <div className="rounded-lg border border-green-300 bg-green-50 px-3 py-2 text-sm text-green-700 dark:border-green-900/50 dark:bg-green-900/20 dark:text-green-200">
              {successMessage}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-200">
              {error}
            </div>
          )}
        </div>
      </Card>

      {/* Order list */}
      <Card title={t('orderList')}>
        {isLoading ? (
          <p className="text-sm text-[var(--foreground-muted)]">{tPortfolio('orderLoading')}</p>
        ) : orders.length === 0 ? (
          <p className="text-sm text-[var(--foreground-muted)]">{t('noOrders')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[940px] text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--foreground-muted)]">
                  <th className="px-2 py-2 font-medium">{tPortfolio('orderId')}</th>
                  <th className="px-2 py-2 font-medium">{tPortfolio('ticker')}</th>
                  <th className="px-2 py-2 font-medium">{tPortfolio('orderSide')}</th>
                  <th className="px-2 py-2 text-right font-medium">{tPortfolio('orderQuantity')}</th>
                  <th className="px-2 py-2 text-right font-medium">{tPortfolio('orderFilledPrice')}</th>
                  <th className="px-2 py-2 text-right font-medium">{tPortfolio('orderUnfilledQty')}</th>
                  <th className="px-2 py-2 font-medium">{tPortfolio('orderStatus')}</th>
                  <th className="px-2 py-2 text-right font-medium">{tPortfolio('actions')}</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => {
                  const canChange = ['RECEIVED', 'CONFIRMED', 'PARTIAL'].includes(order.status);
                  return (
                    <tr key={order.order_id} className="border-b border-[var(--border)]/70">
                      <td className="px-2 py-2 font-mono text-xs text-[var(--foreground)]">
                        {order.order_id}
                      </td>
                      <td className="px-2 py-2 font-mono text-[var(--color-primary)]">
                        {order.ticker}
                      </td>
                      <td className="px-2 py-2">
                        {order.side === 'BUY' ? tPortfolio('orderSideBuy') : tPortfolio('orderSideSell')}
                      </td>
                      <td className="px-2 py-2 text-right font-mono">
                        {order.quantity.toLocaleString(locale)}
                      </td>
                      <td className="px-2 py-2 text-right font-mono">
                        {formatCurrency(order.filled_price ?? order.price, 'USD')}
                      </td>
                      <td className="px-2 py-2 text-right font-mono">
                        {order.unfilled_quantity.toLocaleString(locale)}
                      </td>
                      <td className="px-2 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs ${statusBadgeClass(order.status)}`}>
                          {tPortfolio(`orderStatus_${order.status}`)}
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

      {/* Confirm dialog for live trading */}
      {confirmOpen && pendingOrderRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-5 shadow-xl">
            <div className="mb-3 flex items-center gap-2 text-red-600 dark:text-red-300">
              <AlertTriangle className="h-5 w-5" />
              <h3 className="font-semibold">{tPortfolio('orderConfirmTitle')}</h3>
            </div>
            <p className="text-sm text-[var(--foreground-muted)]">
              {tPortfolio('orderConfirmLiveWarning')}
            </p>
            <div className="mt-4 rounded-lg border border-[var(--border)] p-3 text-sm">
              <p>Broker: <span className="font-mono">{selectedBroker}</span></p>
              <p>{tPortfolio('ticker')}: <span className="font-mono">{pendingOrderRequest.ticker}</span></p>
              <p>{tPortfolio('orderSide')}: {pendingOrderRequest.side === 'BUY' ? tPortfolio('orderSideBuy') : tPortfolio('orderSideSell')}</p>
              <p>{tPortfolio('orderQuantity')}: {pendingOrderRequest.quantity.toLocaleString(locale)}</p>
              <p>{tPortfolio('orderType')}: {pendingOrderRequest.order_type === 'MARKET' ? tPortfolio('orderTypeMarket') : tPortfolio('orderTypeLimit')}</p>
              <p>{tPortfolio('orderPrice')}: {pendingOrderRequest.order_type === 'MARKET' ? '-' : formatCurrency(pendingOrderRequest.price ?? null, 'USD')}</p>
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

      {/* Amend dialog */}
      {amendTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-5 shadow-xl">
            <h3 className="font-semibold text-[var(--foreground)]">{tPortfolio('orderAmendTitle')}</h3>
            <p className="mt-1 text-sm text-[var(--foreground-muted)]">{amendTarget.order_id}</p>
            <div className="mt-4 grid gap-3">
              <input
                type="number"
                min={1}
                value={amendQty}
                onChange={(e) => setAmendQty(e.target.value)}
                placeholder={tPortfolio('orderQuantity')}
                className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm"
              />
              <input
                type="number"
                min={0}
                value={amendPrice}
                onChange={(e) => setAmendPrice(e.target.value)}
                placeholder={tPortfolio('orderPrice')}
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

      {/* Preload order status translations */}
      <div className="sr-only">
        {ORDER_STATUSES.map((status) => (
          <span key={status}>{tPortfolio(`orderStatus_${status}`)}</span>
        ))}
      </div>
    </div>
  );
}
