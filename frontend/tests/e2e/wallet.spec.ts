import { expect, test } from '@playwright/test';

test('wallet modal opens from the launchpad', async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.clear();
  });

  await page.route('http://127.0.0.1:8000/api/marketplace/config', async (route) => {
    await route.fulfill({
      json: {
        trading_enabled: false,
        launch_enabled: false,
        maintenance_reason: 'Pre-launch checks',
        active_factory_app_id: 0,
        deprecated_factory_app_id: 0,
        legacy_factory_app_ids: [],
        cortex_asset_id: 0,
        creation_fee: 100000000,
        buy_fee_bps: 100,
        sell_fee_bps: 200,
        graduation_threshold: 50000000000,
        base_price: 10000,
        slope: 1000,
        next_deployment: {},
        notes: [],
      },
    });
  });

  await page.goto('/marketplace');

  await page.locator('main').getByRole('button', { name: /^connect wallet$/i }).first().click();

  await expect(page.getByRole('heading', { name: /connect wallet/i })).toBeVisible();
  await expect(page.getByText(/select your algorand wallet/i)).toBeVisible();
  await expect(page.getByText(/powered by algorand/i)).toBeVisible();
});
