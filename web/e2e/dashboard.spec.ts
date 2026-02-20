/**
 * E2E tests for the Dashboard page (/en).
 *
 * Verifies that the main landing page loads correctly, displays the expected
 * heading, connection status badge, and the four dashboard cards.
 */

import { test, expect } from './fixtures';

test.describe('Dashboard page', () => {
  test.beforeEach(async ({ mockApi }) => {
    await mockApi();
  });

  test('page loads with correct title', async ({ page }) => {
    await page.goto('/en');
    await expect(page).toHaveTitle(/Quant Investment/);
  });

  test('dashboard heading is visible', async ({ page }) => {
    await page.goto('/en');
    const heading = page.getByRole('heading', { name: 'Dashboard' });
    await expect(heading).toBeVisible();
  });

  test('connection status badge shows API Connected', async ({ page }) => {
    await page.goto('/en');

    // Wait for the health check to complete and show the connected badge
    const badge = page.getByText('API Connected');
    await expect(badge).toBeVisible({ timeout: 10_000 });
  });

  test('dashboard cards render', async ({ page }) => {
    await page.goto('/en');

    // PortfolioSummaryCard
    await expect(page.getByText('Portfolio Overview')).toBeVisible({ timeout: 10_000 });

    // SellSignalsCard
    await expect(page.getByText('Sell Signals')).toBeVisible();

    // RecentReportsCard
    await expect(page.getByText('Recent Reports')).toBeVisible();

    // QuickActionsCard
    await expect(page.getByText('Quick Actions')).toBeVisible();
  });

  test('no console errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/en');
    // Give hydration and data fetching time to settle
    await page.waitForTimeout(2_000);

    expect(errors).toEqual([]);
  });
});
