import { test, expect } from './fixtures';

test.describe('Visual regression', () => {
  test('dashboard screenshot', async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/');
    await expect(page.getByText('API Connected')).toBeVisible();

    await expect(page).toHaveScreenshot('dashboard.png', {
      maxDiffPixelRatio: 0.01,
      fullPage: true,
    });
  });

  test('portfolio screenshot', async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/en/portfolio');
    await expect(page.getByText('AAPL')).toBeVisible();

    await expect(page).toHaveScreenshot('portfolio.png', {
      maxDiffPixelRatio: 0.01,
      fullPage: true,
    });
  });
});
