import { expect, test } from '@playwright/test';

test('marketplace excludes the bootstrap CORTEX asset and opens buy details', async ({ page }) => {
  await page.route('https://testnet-idx.algonode.cloud/v2/transactions?application-id=*&tx-type=appl&limit=50', async (route) => {
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

  await page.route('https://testnet-idx.algonode.cloud/v2/assets/757199999/balances?currency-greater-than=0&limit=100', async (route) => {
    await route.fulfill({
      json: {
        balances: [
          { amount: 2_000_000 },
          { amount: 1_000_000 },
        ],
      },
    });
  });

  await page.goto('/marketplace');

  await expect(page.getByText('Neural Scout')).toBeVisible();
  await expect(page.getByText('ASA 757172171')).toHaveCount(0);

  await page.getByRole('button', { name: /^buy$/i }).click();

  await expect(page.getByText(/buy tokens/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /buy on testnet/i })).toBeDisabled();
});
