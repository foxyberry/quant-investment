/**
 * E2E tests for the Screening page (/en/screening).
 *
 * Verifies that the screening page loads and displays the expected heading
 * and filter panel.
 */

import { test, expect } from './fixtures';

test.describe('Screening page', () => {
  test.beforeEach(async ({ mockApi }) => {
    await mockApi();
  });

  test('page loads successfully', async ({ page }) => {
    await page.goto('/en/screening');
    await expect(page).toHaveTitle(/Quant Investment/);
  });

  test('screening heading is visible', async ({ page }) => {
    await page.goto('/en/screening');
    const heading = page.getByRole('heading', { name: 'Stock Screening' });
    await expect(heading).toBeVisible();
  });

  test('subtitle text is visible', async ({ page }) => {
    await page.goto('/en/screening');
    await expect(
      page.getByText('Filter stocks based on predefined screening criteria')
    ).toBeVisible();
  });

  test('no console errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/en/screening');
    await page.waitForTimeout(2_000);

    expect(errors).toEqual([]);
  });
});
