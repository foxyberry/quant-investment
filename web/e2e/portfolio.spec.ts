import { test, expect } from './fixtures';

test.describe('Portfolio page', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/en/portfolio');
  });

  test('page loads', async ({ page }) => {
    await expect(page).toHaveTitle(/Quant/i);
  });

  test('portfolio heading is visible', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /portfolio/i });
    await expect(heading).toBeVisible();
  });

  test('holdings render with AAPL and GOOGL', async ({ page }) => {
    await expect(page.getByText('AAPL')).toBeVisible();
    await expect(page.getByText('GOOGL')).toBeVisible();
  });

  test('summary cards are visible', async ({ page }) => {
    await expect(page.getByText('Total Investment')).toBeVisible();
    await expect(page.getByText('Market Value')).toBeVisible();
  });

  test('add holding button is visible', async ({ page }) => {
    const addButton = page.getByRole('button', { name: /add.*holding/i });
    await expect(addButton).toBeVisible();
  });

  test('no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/en/portfolio');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });
});
