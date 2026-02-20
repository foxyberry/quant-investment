/**
 * E2E tests for the Strategy Builder page (/en/strategy).
 *
 * Verifies that the strategy canvas loads, displays the breadcrumb/toolbar
 * heading, and renders the ReactFlow canvas area.
 */

import { test, expect } from './fixtures';

test.describe('Strategy Builder page', () => {
  test.beforeEach(async ({ mockApi }) => {
    await mockApi();
  });

  test('page loads successfully', async ({ page }) => {
    await page.goto('/en/strategy');
    await expect(page).toHaveTitle(/Quant Investment/);
  });

  test('strategy canvas heading is visible', async ({ page }) => {
    await page.goto('/en/strategy');

    // The toolbar breadcrumb shows "QuantCanvas" as the title
    const heading = page.getByText('QuantCanvas');
    await expect(heading).toBeVisible({ timeout: 10_000 });
  });

  test('deploy strategy button is visible', async ({ page }) => {
    await page.goto('/en/strategy');

    const deployButton = page.getByRole('button', { name: /Deploy Strategy/i });
    await expect(deployButton).toBeVisible({ timeout: 10_000 });
  });

  test('save strategy button is visible', async ({ page }) => {
    await page.goto('/en/strategy');

    const saveButton = page.getByRole('button', { name: /Save Strategy/i });
    await expect(saveButton).toBeVisible({ timeout: 10_000 });
  });

  test('no console errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/en/strategy');
    // Strategy page uses ReactFlow which may take longer to initialize
    await page.waitForTimeout(3_000);

    expect(errors).toEqual([]);
  });
});
