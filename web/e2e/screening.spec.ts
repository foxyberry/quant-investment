import { test, expect } from './fixtures';

test.describe('Screening page', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/en/screening');
  });

  test('page loads', async ({ page }) => {
    await expect(page).toHaveTitle(/Quant/i);
  });

  test('screening heading is visible', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /stock screening/i });
    await expect(heading).toBeVisible();
  });

  test('subtitle text is visible', async ({ page }) => {
    const subtitle = page.getByText(/screen.*stocks/i);
    await expect(subtitle).toBeVisible();
  });

  test('no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/en/screening');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });
});
