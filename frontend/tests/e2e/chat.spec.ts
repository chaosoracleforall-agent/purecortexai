import { expect, test } from '@playwright/test';

test('chat gate requires an API key', async ({ page }) => {
  await page.goto('/chat');

  await expect(page.getByText(/unlock neural link/i)).toBeVisible();
  await page.getByRole('button', { name: /start secure session/i }).click();
  await expect(page.getByText(/paste a valid api key first/i)).toBeVisible();
});
