import { expect, test } from '@playwright/test';

function encodeUint64(value: bigint): Uint8Array {
  const bytes = new Uint8Array(8);
  const view = new DataView(bytes.buffer);
  view.setBigUint64(0, value);
  return bytes;
}

function buildCurveConfigBase64(): string {
  const bytes = new Uint8Array(40);
  const view = new DataView(bytes.buffer);
  view.setBigUint64(0, 10_000n); // base_price
  view.setBigUint64(8, 1_000n); // slope
  view.setBigUint64(16, 100n); // buy_fee_bps
  view.setBigUint64(24, 200n); // sell_fee_bps
  view.setBigUint64(32, 50_000_000_000n); // graduation_threshold
  return Buffer.from(bytes).toString('base64');
}

test('marketplace excludes the bootstrap CORTEX asset and opens buy details', async ({ page }) => {
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

  await page.route(/https:\/\/\w+-idx\.algonode\.cloud\/v2\/transactions\?application-id=.*tx-type=appl.*limit=50/, async (route) => {
    await route.fulfill({
      json: {
        transactions: [
          {
            'inner-txns': [
              {
                'tx-type': 'acfg',
                'created-asset-index': 757172171,
                'asset-config-transaction': {
                  params: {
                    name: 'PURECORTEX',
                    'unit-name': 'CORTEX',
                  },
                },
              },
            ],
          },
          {
            'inner-txns': [
              {
                'tx-type': 'acfg',
                'created-asset-index': 757199999,
                'asset-config-transaction': {
                  params: {
                    name: 'Neural Scout',
                    'unit-name': 'NSCT',
                  },
                },
              },
            ],
          },
        ],
      },
    });
  });

  await page.route('https://*-idx.algonode.cloud/v2/assets/757199999/balances?currency-greater-than=0&limit=100', async (route) => {
    await route.fulfill({
      json: {
        balances: [
          { amount: 2_000_000 },
          { amount: 1_000_000 },
        ],
      },
    });
  });

  await page.route('https://*-api.algonode.cloud/v2/applications/*/box?name=*', async (route) => {
    const requestUrl = new URL(route.request().url());
    const rawName = requestUrl.searchParams.get('name') || '';
    const encoded = rawName.startsWith('b64:') ? rawName.slice(4) : rawName;
    const decoded = Buffer.from(decodeURIComponent(encoded), 'base64').toString('latin1');
    const prefix = decoded[0];
    const isSupply = prefix === 's';
    await route.fulfill({
      json: {
        value: isSupply
          ? Buffer.from(encodeUint64(3_000_000n)).toString('base64')
          : buildCurveConfigBase64(),
      },
    });
  });

  await page.goto('/marketplace');
  await page.waitForResponse((response) =>
    response.url().includes('/v2/transactions?application-id=') && response.request().method() === 'GET',
  );

  await expect(page.getByText('Neural Scout')).toBeVisible();
  await expect(page.getByText('ASA 757172171')).toHaveCount(0);

  await page.getByRole('button', { name: /^buy$/i }).click();

  await expect(page.getByText(/buy tokens/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /trading paused/i }).first()).toBeDisabled();
});
