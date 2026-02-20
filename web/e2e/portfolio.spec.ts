/**
 * E2E tests for the Portfolio page (/en/portfolio).
 *
 * Verifies that the portfolio page loads, displays the heading, and renders
 * the holdings table/list with mocked data (AAPL, GOOGL).
 */

import { test, expect } from './fixtures';

test.describe('Portfolio page', () => {
  test.beforeEach(async ({ mockApi }) => {
    await mockApi();
  });

  test('page loads successfully', async ({ page }) => {
    await page.goto('/en/portfolio');
    await expect(page).toHaveTitle(/Quant Investment/);
  });

  test('portfolio heading is visible', async ({ page }) => {
    await page.goto('/en/portfolio');
    const heading = page.getByRole('heading', { name: 'Portfolio' });
    await expect(heading).toBeVisible();
  });

  test('holdings render with mocked data', async ({ page }) => {
    await page.goto('/en/portfolio');

    // Wait for data to load and render
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('GOOGL')).toBeVisible();
  });

  test('portfolio summary cards are visible when data loads', async ({ page }) => {
    await page.goto('/en/portfolio');

    // Summary cards should appear after data loads
    await expect(page.getByText('Total Investment')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Market Value')).toBeVisible();
  });

  test('add holding button is visible', async ({ page }) => {
    await page.goto('/en/portfolio');
    const addButton = page.getByRole('button', { name: /Add Holding/i });
    await expect(addButton).toBeVisible();
  });

  test('no console errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/en/portfolio');
    await page.waitForTimeout(2_000);

    expect(errors).toEqual([]);
  });
});
