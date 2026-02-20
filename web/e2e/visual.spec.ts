/**
 * Visual regression tests.
 *
 * Captures full-page screenshots of key pages and compares them against
 * baseline snapshots.  Uses `maxDiffPixelRatio: 0.01` to tolerate minor
 * rendering differences (e.g. anti-aliasing, font hinting) across runs.
 *
 * All API calls are mocked so pages render deterministically.
 */

import { test, expect } from './fixtures';

test.describe('Visual regression', () => {
  test.beforeEach(async ({ mockApi }) => {
    await mockApi();
  });

  test('dashboard screenshot', async ({ page }) => {
    await page.goto('/en');

    // Wait for the connection badge and cards to settle
    await page.getByText('API Connected').waitFor({ state: 'visible', timeout: 10_000 });
    // Extra pause for animations / layout shifts
    await page.waitForTimeout(1_000);

    await expect(page).toHaveScreenshot('dashboard.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });

  test('portfolio page screenshot', async ({ page }) => {
    await page.goto('/en/portfolio');

    // Wait for holdings data to render
    await page.getByText('AAPL').waitFor({ state: 'visible', timeout: 10_000 });
    await page.waitForTimeout(1_000);

    await expect(page).toHaveScreenshot('portfolio.png', {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });
});
