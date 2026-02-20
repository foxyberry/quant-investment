import { test, expect } from './fixtures';

test.describe('Dashboard page', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/');
  });

  test('page loads with title', async ({ page }) => {
    await expect(page).toHaveTitle(/Quant/i);
  });

  test('dashboard heading is visible', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /dashboard/i });
    await expect(heading).toBeVisible();
  });

  test('connection status badge shows API Connected', async ({ page }) => {
    const badge = page.getByText('API Connected');
    await expect(badge).toBeVisible();
  });

  test('dashboard cards render', async ({ page }) => {
    await expect(page.getByText('Portfolio Overview')).toBeVisible();
    await expect(page.getByText('Sell Signals')).toBeVisible();
    await expect(page.getByText('Recent Reports')).toBeVisible();
    await expect(page.getByText('Quick Actions')).toBeVisible();
  });

  test('no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });
});
