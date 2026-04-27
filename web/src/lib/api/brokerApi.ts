import type {
  KiwoomConnectionStatus,
  KiwoomConnectionState,
  KiwoomCondition,
  KiwoomConditionMatch,
  KiwoomOrder,
  KiwoomOrderRequest,
  BrokerConnectionStatus,
  BrokerKillSwitchResult,
  BrokerOrder,
  BrokerOrderRequest,
  TigerSettings,
  TigerSettingsUpsert,
  IBKRSettings,
  IBKRSettingsUpsert,
  TelegramSettings,
  TelegramSettingsUpsert,
  TelegramTestResult,
} from '../types';
import { fetchApi, API_BASE_URL } from './_base';

function normalizeKiwoomStatus(raw: Record<string, unknown>): KiwoomConnectionStatus {
  const rawStatus = typeof raw.status === 'string' ? raw.status.toLowerCase() : '';
  const booleanConnected =
    typeof raw.connected === 'boolean'
      ? raw.connected
      : typeof raw.is_connected === 'boolean'
      ? raw.is_connected
      : null;

  let status: KiwoomConnectionState = 'unavailable';
  if (rawStatus === 'connected' || rawStatus === 'disconnected' || rawStatus === 'connecting') {
    status = rawStatus;
  } else if (booleanConnected === true) {
    status = 'connected';
  } else if (booleanConnected === false) {
    status = 'disconnected';
  }

  const accountsRaw = raw.accounts;
  const accounts = Array.isArray(accountsRaw)
    ? accountsRaw.filter((v): v is string => typeof v === 'string')
    : typeof accountsRaw === 'string'
    ? accountsRaw
        .split(';')
        .map((v) => v.trim())
        .filter((v) => v.length > 0)
    : [];

  return {
    status,
    is_mock_trading:
      typeof raw.is_mock_trading === 'boolean'
        ? raw.is_mock_trading
        : typeof raw.mock_trading === 'boolean'
        ? raw.mock_trading
        : null,
    user_id:
      typeof raw.user_id === 'string'
        ? raw.user_id
        : typeof raw.userId === 'string'
        ? raw.userId
        : null,
    accounts,
    updated_at: typeof raw.updated_at === 'string' ? raw.updated_at : null,
  };
}

export async function getKiwoomConnectionStatus(): Promise<KiwoomConnectionStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/kiwoom/connection/status`);
    if (!response.ok) {
      return {
        status: 'unavailable',
        is_mock_trading: null,
        user_id: null,
        accounts: [],
        updated_at: null,
      };
    }
    const raw = (await response.json()) as Record<string, unknown>;
    const payload =
      raw.data && typeof raw.data === 'object'
        ? (raw.data as Record<string, unknown>)
        : raw;
    return normalizeKiwoomStatus(payload);
  } catch {
    return {
      status: 'unavailable',
      is_mock_trading: null,
      user_id: null,
      accounts: [],
      updated_at: null,
    };
  }
}

export async function getKiwoomConditionList(): Promise<KiwoomCondition[]> {
  const raw = await fetchApi<unknown>('/api/kiwoom/conditions');
  const asRecord = (v: unknown): Record<string, unknown> | null =>
    v && typeof v === 'object' ? (v as Record<string, unknown>) : null;
  const normalize = (item: unknown): KiwoomCondition | null => {
    const record = asRecord(item);
    if (!record) return null;
    const indexRaw = record.index ?? record.condition_index ?? record.id;
    const nameRaw = record.name ?? record.condition_name ?? record.label;
    const index = typeof indexRaw === 'number' ? indexRaw : Number(indexRaw);
    const name = typeof nameRaw === 'string' ? nameRaw : null;
    if (!Number.isFinite(index) || !name) return null;
    return { index, name };
  };

  if (Array.isArray(raw)) {
    return raw.map(normalize).filter((v): v is KiwoomCondition => v !== null);
  }

  const payload = asRecord(raw);
  const listCandidate = payload?.conditions ?? payload?.data;
  if (Array.isArray(listCandidate)) {
    return listCandidate.map(normalize).filter((v): v is KiwoomCondition => v !== null);
  }
  return [];
}

export async function startKiwoomConditionMonitor(condition: KiwoomCondition): Promise<void> {
  await fetchApi('/api/kiwoom/conditions/start', {
    method: 'POST',
    body: JSON.stringify({
      condition_index: condition.index,
      condition_name: condition.name,
    }),
  });
}

export async function stopKiwoomConditionMonitor(condition: KiwoomCondition): Promise<void> {
  await fetchApi('/api/kiwoom/conditions/stop', {
    method: 'POST',
    body: JSON.stringify({
      condition_index: condition.index,
      condition_name: condition.name,
    }),
  });
}

export async function getKiwoomConditionMatches(condition: KiwoomCondition): Promise<KiwoomConditionMatch[]> {
  const raw = await fetchApi<unknown>(
    `/api/kiwoom/conditions/matches?condition_index=${encodeURIComponent(String(condition.index))}&condition_name=${encodeURIComponent(condition.name)}`
  );
  const asRecord = (v: unknown): Record<string, unknown> | null =>
    v && typeof v === 'object' ? (v as Record<string, unknown>) : null;
  const normalize = (item: unknown): KiwoomConditionMatch | null => {
    const record = asRecord(item);
    if (!record) return null;
    const tickerRaw = record.ticker ?? record.code ?? record.symbol;
    const ticker = typeof tickerRaw === 'string' ? tickerRaw : null;
    if (!ticker) return null;
    const priceRaw = record.current_price ?? record.price ?? null;
    const price =
      typeof priceRaw === 'number'
        ? priceRaw
        : typeof priceRaw === 'string'
        ? Number(priceRaw.replace(/,/g, ''))
        : null;
    return {
      ticker,
      name: typeof record.name === 'string' ? record.name : null,
      current_price: Number.isFinite(price as number) ? (price as number) : null,
      updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
    };
  };

  if (Array.isArray(raw)) {
    return raw.map(normalize).filter((v): v is KiwoomConditionMatch => v !== null);
  }
  const payload = asRecord(raw);
  const listCandidate = payload?.matches ?? payload?.stocks ?? payload?.data;
  if (Array.isArray(listCandidate)) {
    return listCandidate.map(normalize).filter((v): v is KiwoomConditionMatch => v !== null);
  }
  return [];
}

function normalizeKiwoomOrder(raw: unknown): KiwoomOrder | null {
  const record = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : null;
  if (!record) return null;

  const orderIdRaw = record.order_id ?? record.order_no ?? record.id;
  const tickerRaw = record.ticker ?? record.code ?? record.symbol;
  const sideRaw = record.side ?? record.order_side ?? 'BUY';
  const orderTypeRaw = record.order_type ?? record.hoga ?? 'LIMIT';
  const statusRaw = record.status ?? record.order_status ?? 'RECEIVED';
  const quantityRaw = record.quantity ?? record.order_qty ?? 0;
  const filledQtyRaw = record.filled_quantity ?? record.executed_qty ?? 0;
  const unfilledQtyRaw = record.unfilled_quantity ?? record.remaining_qty ?? 0;
  const priceRaw = record.price ?? record.order_price ?? null;
  const filledPriceRaw = record.filled_price ?? record.executed_price ?? null;
  const createdAtRaw = record.created_at ?? record.ordered_at ?? new Date().toISOString();

  const toNumber = (value: unknown): number | null => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
      const parsed = Number(value.replace(/,/g, ''));
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  };

  const orderId = typeof orderIdRaw === 'string' ? orderIdRaw : String(orderIdRaw ?? '');
  const ticker = typeof tickerRaw === 'string' ? tickerRaw : '';
  if (!orderId || !ticker) return null;

  const side = sideRaw === 'SELL' ? 'SELL' : 'BUY';
  const orderType = orderTypeRaw === 'MARKET' ? 'MARKET' : 'LIMIT';
  const allowedStatuses = ['RECEIVED', 'CONFIRMED', 'FILLED', 'CANCELED', 'REJECTED', 'PARTIAL'] as const;
  const status = allowedStatuses.includes(statusRaw as (typeof allowedStatuses)[number])
    ? (statusRaw as (typeof allowedStatuses)[number])
    : 'RECEIVED';

  return {
    order_id: orderId,
    ticker,
    side,
    quantity: toNumber(quantityRaw) ?? 0,
    filled_quantity: toNumber(filledQtyRaw) ?? 0,
    unfilled_quantity: toNumber(unfilledQtyRaw) ?? 0,
    order_type: orderType,
    price: toNumber(priceRaw),
    filled_price: toNumber(filledPriceRaw),
    status,
    created_at: typeof createdAtRaw === 'string' ? createdAtRaw : new Date().toISOString(),
    updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
  };
}

export async function placeKiwoomOrder(request: KiwoomOrderRequest): Promise<KiwoomOrder> {
  const raw = await fetchApi<unknown>('/api/kiwoom/orders', {
    method: 'POST',
    body: JSON.stringify(request),
  });
  const normalized = normalizeKiwoomOrder(raw);
  if (!normalized) {
    throw new Error('Invalid order response');
  }
  return normalized;
}

export async function getKiwoomOrders(): Promise<KiwoomOrder[]> {
  const raw = await fetchApi<unknown>('/api/kiwoom/orders');
  const payload = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : null;
  const list = Array.isArray(raw)
    ? raw
    : Array.isArray(payload?.orders)
    ? payload?.orders
    : Array.isArray(payload?.data)
    ? payload?.data
    : [];
  return list.map(normalizeKiwoomOrder).filter((v): v is KiwoomOrder => v !== null);
}

export async function cancelKiwoomOrder(orderId: string): Promise<void> {
  await fetchApi<void>(`/api/kiwoom/orders/${encodeURIComponent(orderId)}/cancel`, {
    method: 'POST',
  });
}

export async function amendKiwoomOrder(
  orderId: string,
  data: { quantity?: number; price?: number | null }
): Promise<void> {
  await fetchApi<void>(`/api/kiwoom/orders/${encodeURIComponent(orderId)}/amend`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function triggerKiwoomKillSwitch(): Promise<void> {
  await fetchApi<void>('/api/kiwoom/orders/kill-switch', {
    method: 'POST',
  });
}

// Unified Broker API functions

export async function listBrokers(): Promise<string[]> {
  const data = await fetchApi<{ brokers: string[] }>('/api/brokers/');
  return data.brokers;
}

export async function getSettingsBrokerStatuses(): Promise<BrokerConnectionStatus[]> {
  const data = await fetchApi<{ brokers: BrokerConnectionStatus[] }>('/api/settings/brokers');
  return data.brokers;
}

export async function getTigerSettings(): Promise<TigerSettings> {
  return fetchApi<TigerSettings>('/api/settings/brokers/tiger');
}

export async function saveTigerSettings(payload: TigerSettingsUpsert): Promise<TigerSettings> {
  return fetchApi<TigerSettings>('/api/settings/brokers/tiger', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testTigerConnection(): Promise<BrokerConnectionStatus> {
  return fetchApi<BrokerConnectionStatus>('/api/settings/brokers/tiger/test', {
    method: 'POST',
  });
}

export async function getIbkrSettings(): Promise<IBKRSettings> {
  return fetchApi<IBKRSettings>('/api/settings/brokers/ibkr');
}

export async function saveIbkrSettings(payload: IBKRSettingsUpsert): Promise<IBKRSettings> {
  return fetchApi<IBKRSettings>('/api/settings/brokers/ibkr', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testIbkrConnection(): Promise<BrokerConnectionStatus> {
  return fetchApi<BrokerConnectionStatus>('/api/settings/brokers/ibkr/test', {
    method: 'POST',
  });
}

export async function getTelegramSettings(): Promise<TelegramSettings> {
  return fetchApi<TelegramSettings>('/api/settings/telegram');
}

export async function saveTelegramSettings(payload: TelegramSettingsUpsert): Promise<TelegramSettings> {
  return fetchApi<TelegramSettings>('/api/settings/telegram', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testTelegramNotification(): Promise<TelegramTestResult> {
  return fetchApi<TelegramTestResult>('/api/settings/telegram/test', {
    method: 'POST',
  });
}

// Slack notification settings

export interface SlackSettings {
  has_webhook_url: boolean;
  channel_name: string | null;
  enabled: boolean;
  updated_at: string | null;
}

export interface SlackSettingsUpsert {
  webhook_url?: string;
  channel_name?: string;
  enabled: boolean;
}

export interface SlackTestResult {
  success: boolean;
  message: string;
}

export async function getSlackSettings(): Promise<SlackSettings> {
  return fetchApi<SlackSettings>('/api/settings/slack');
}

export async function saveSlackSettings(payload: SlackSettingsUpsert): Promise<SlackSettings> {
  return fetchApi<SlackSettings>('/api/settings/slack', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testSlackNotification(): Promise<SlackTestResult> {
  return fetchApi<SlackTestResult>('/api/settings/slack/test', {
    method: 'POST',
  });
}

export async function getBrokerConnectionStatus(
  broker: string
): Promise<BrokerConnectionStatus> {
  return fetchApi<BrokerConnectionStatus>(
    `/api/brokers/${encodeURIComponent(broker)}/status`
  );
}

export async function placeBrokerOrder(
  broker: string,
  order: BrokerOrderRequest
): Promise<BrokerOrder> {
  return fetchApi<BrokerOrder>(
    `/api/brokers/${encodeURIComponent(broker)}/orders`,
    {
      method: 'POST',
      body: JSON.stringify(order),
    }
  );
}

export async function getBrokerOrders(broker: string): Promise<BrokerOrder[]> {
  return fetchApi<BrokerOrder[]>(
    `/api/brokers/${encodeURIComponent(broker)}/orders`
  );
}

export async function cancelBrokerOrder(
  broker: string,
  orderId: string
): Promise<void> {
  await fetchApi<void>(
    `/api/brokers/${encodeURIComponent(broker)}/orders/${encodeURIComponent(orderId)}`,
    { method: 'DELETE' }
  );
}

export async function amendBrokerOrder(
  broker: string,
  orderId: string,
  amend: { quantity?: number; price?: number | null }
): Promise<void> {
  await fetchApi<void>(
    `/api/brokers/${encodeURIComponent(broker)}/orders/${encodeURIComponent(orderId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(amend),
    }
  );
}

export async function triggerBrokerKillSwitch(
  broker: string
): Promise<BrokerKillSwitchResult> {
  return fetchApi<BrokerKillSwitchResult>(
    `/api/brokers/${encodeURIComponent(broker)}/kill-switch`,
    { method: 'POST' }
  );
}
