/**
 * Shared Playwright test fixtures for E2E tests.
 *
 * Exports a custom `test` that extends Playwright's base test with a `mockApi`
 * fixture.  When a test calls `await mockApi()`, all fetch requests matching
 * the backend origin (localhost:8000) are intercepted by `page.route()` so the
 * tests run without a real API server.
 */

import { test as base, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Route handler helper
// ---------------------------------------------------------------------------

async function installApiMocks(page: Page) {
  // Match any request to localhost:8000
  await page.route('**/localhost:8000/**', async (route) => {
    const url = route.request().url();

    // Health check
    if (url.includes('/health')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      });
    }

    // Portfolio holdings
    if (url.includes('/api/portfolio/holdings')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_HOLDINGS),
      });
    }

    // Portfolio summary
    if (url.includes('/api/portfolio/summary')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_PORTFOLIO_SUMMARY),
      });
    }

    // Sell signals
    if (url.includes('/api/portfolio/sell-signals')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ signals: [], checked_at: new Date().toISOString() }),
      });
    }

    // Analysis reports
    if (url.includes('/api/analysis/reports')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ reports: [], total_count: 0 }),
      });
    }

    // Analysis status
    if (url.includes('/api/analysis/status')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ is_running: false }),
      });
    }

    // Screening presets
    if (url.includes('/api/screening/presets')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    }

    // Screening universes
    if (url.includes('/api/screening/universes')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    }

    // Strategy conditions
    if (url.includes('/api/strategy/conditions')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ conditions: [] }),
      });
    }

    // Saved strategies
    if (url.includes('/api/strategy/saved')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ strategies: [] }),
      });
    }

    // Strategy sectors
    if (url.includes('/api/strategy/sectors')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ sectors: [] }),
      });
    }

    // Fallback: return 404 for any unhandled API route
    return route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Mock: endpoint not configured' }),
    });
  });
}

// ---------------------------------------------------------------------------
// Custom test fixture
// ---------------------------------------------------------------------------

type MockApiFixture = {
  /** Call `await mockApi()` to intercept all API requests with mock data. */
  mockApi: () => Promise<void>;
};

export const test = base.extend<MockApiFixture>({
  // eslint-disable-next-line react-hooks/rules-of-hooks
  mockApi: async ({ page }, use) => {
    const setup = async () => {
      await installApiMocks(page);
    };
    await use(setup);
  },
});

export { expect } from '@playwright/test';
