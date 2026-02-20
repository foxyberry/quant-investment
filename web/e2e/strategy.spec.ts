import { test, expect } from './fixtures';

test.describe('Strategy page', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/en/strategy');
  });

  test('page loads', async ({ page }) => {
    await expect(page).toHaveTitle(/Quant/i);
  });

  test('QuantCanvas heading is visible', async ({ page }) => {
    const heading = page.getByRole('heading', { name: /quantcanvas/i });
    await expect(heading).toBeVisible();
  });

  test('Deploy Strategy button is visible', async ({ page }) => {
    const deployButton = page.getByRole('button', { name: /deploy.*strategy/i });
    await expect(deployButton).toBeVisible();
  });

  test('Save Strategy button is visible', async ({ page }) => {
    const saveButton = page.getByRole('button', { name: /save.*strategy/i });
    await expect(saveButton).toBeVisible();
  });

  test('no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/en/strategy');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });
});
