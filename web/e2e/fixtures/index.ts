import { test as base, type Page } from '@playwright/test';

const MOCK_HOLDINGS = [
  {
    ticker: 'AAPL',
    name: 'Apple Inc.',
    quantity: 50,
    avg_price: 145.0,
    current_price: 178.5,
    market_value: 8925.0,
    pnl: 1675.0,
    pnl_pct: 23.1,
    currency: 'USD',
  },
  {
    ticker: 'GOOGL',
    name: 'Alphabet Inc.',
    quantity: 20,
    avg_price: 120.0,
    current_price: 142.3,
    market_value: 2846.0,
    pnl: 446.0,
    pnl_pct: 18.58,
    currency: 'USD',
  },
];

const MOCK_PORTFOLIO_SUMMARY = {
  total_investment: 9650.0,
  total_market_value: 11771.0,
  total_pnl: 2121.0,
  total_pnl_pct: 21.98,
  holdings_count: 2,
  currency: 'USD',
};

async function installApiMocks(page: Page) {
  // Health endpoint is outside /api/ path, so it needs a separate route
  await page.route('**/health', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) });
  });

  await page.route('**/api/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/api/portfolio/holdings')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_HOLDINGS) });
    }
    if (url.includes('/api/portfolio/summary')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PORTFOLIO_SUMMARY) });
    }
    if (url.includes('/api/portfolio/sell-signals')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ signals: [
        { ticker: 'MSFT', name: 'Microsoft Corp.', signal_type: 'stop_loss', reason: 'Price below stop loss', current_price: 380.0, trigger_price: 370.0, avg_price: 350.0, pnl_pct: 8.57, currency: 'USD' },
      ], checked_at: new Date().toISOString() }) });
    }
    if (url.includes('/api/exchange-rates')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ base: 'USD', rates: { KRW: 1350.5, SGD: 1.34, JPY: 149.8, EUR: 0.92, GBP: 0.79, CNY: 7.24, HKD: 7.82 }, updated_at: new Date().toISOString() }) });
    }
    if (url.includes('/api/analysis/reports')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ reports: [], total_count: 0 }) });
    }
    if (url.includes('/api/analysis/status')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ is_running: false }) });
    }
    if (url.includes('/api/screening/presets')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    if (url.includes('/api/screening/universes')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    if (url.includes('/api/strategy/conditions')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ conditions: [
        { key: 'return_turnaround', label: 'Return Turnaround', description: 'Prev N-day return <= threshold and recent N-day return >= threshold', category: 'price', recommended: false, order: 60, params: [
          { name: 'period_days', type: 'int', default: 5, description: 'Return period (days)' },
          { name: 'prev_max_return_pct', type: 'float', default: -2.0, description: 'Max previous return %' },
          { name: 'min_return_pct', type: 'float', default: 2.0, description: 'Min recent return %' },
        ] },
        { key: 'rsi_oversold', label: 'RSI Oversold', description: 'RSI below threshold', category: 'rsi', recommended: true, order: 10, params: [
          { name: 'period', type: 'int', default: 14, description: 'RSI period' },
          { name: 'threshold', type: 'float', default: 30.0, description: 'RSI threshold' },
        ] },
      ], categories: ['price', 'rsi'] }) });
    }
    if (url.includes('/api/strategy/saved')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ strategies: [] }) });
    }
    if (url.includes('/api/strategy/sectors')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sectors: [] }) });
    }
    return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Mock: endpoint not configured' }) });
  });
}

type MockApiFixture = {
  mockApi: () => Promise<void>;
};

export const test = base.extend<MockApiFixture>({
  mockApi: async ({ page }, use) => {
    const setup = async () => {
      await installApiMocks(page);
    };
    await use(setup); // eslint-disable-line react-hooks/rules-of-hooks -- Playwright fixture API, not a React hook
  },
});

export { expect } from '@playwright/test';
