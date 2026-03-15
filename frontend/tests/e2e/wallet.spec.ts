import { expect, test } from '@playwright/test';

test('wallet modal opens from the launchpad', async ({ page }) => {
  await page.goto('/marketplace');

  await page.getByRole('button', { name: /connect wallet/i }).click();

  await expect(page.getByRole('heading', { name: /connect wallet/i })).toBeVisible();
  await expect(page.getByText(/select your algorand wallet/i)).toBeVisible();
  await expect(page.getByText(/powered by algorand/i)).toBeVisible();
});
