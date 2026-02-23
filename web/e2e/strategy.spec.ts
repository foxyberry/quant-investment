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

  test('return_turnaround condition appears in Price category', async ({ page }) => {
    // Wait for conditions to load from mock API
    const priceCategory = page.getByRole('button', { name: /Price/i });
    await expect(priceCategory).toBeVisible({ timeout: 10000 });

    // Return Turnaround label should be visible in the palette
    const conditionLabel = page.getByText('Return Turnaround', { exact: true });
    await expect(conditionLabel).toBeVisible();
  });

  test('return_turnaround condition shows description', async ({ page }) => {
    const description = page.getByText(/Prev N-day return.*threshold/i);
    await expect(description).toBeVisible({ timeout: 10000 });
  });

  test('condition categories render from mock data', async ({ page }) => {
    // Verify both mock categories appear
    const priceCategory = page.getByRole('button', { name: /Price/i });
    const rsiCategory = page.getByRole('button', { name: /RSI/i });
    await expect(priceCategory).toBeVisible({ timeout: 10000 });
    await expect(rsiCategory).toBeVisible();
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

test.describe('Strategy page i18n', () => {
  test('return_turnaround renders in Korean', async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/ko/strategy');

    const conditionLabel = page.getByText('수익률 전환', { exact: true });
    await expect(conditionLabel).toBeVisible({ timeout: 10000 });
  });

  test('return_turnaround renders in Chinese', async ({ page, mockApi }) => {
    await mockApi();
    await page.goto('/zh/strategy');

    const conditionLabel = page.getByText('收益率反转', { exact: true });
    await expect(conditionLabel).toBeVisible({ timeout: 10000 });
  });
});
